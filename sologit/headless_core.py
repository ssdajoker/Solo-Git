"""FastAPI application exposing the Solo Git headless core."""

from __future__ import annotations

import base64
import binascii
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from fastapi import FastAPI, HTTPException, Query, status
from pydantic import BaseModel, Field

from sologit.api.service import SoloGitService
from sologit.engines.git_engine import GitEngineError, WorkpadNotFoundError

app = FastAPI(
    title="Solo Git Headless Core",
    version="0.1.0",
    description=(
        "Headless service that powers the fused Solo Git interface. "
        "All CLIs, TUIs, and GUIs should route through this API."
    ),
)

service = SoloGitService()


class WorkpadCreateRequest(BaseModel):
    """Request body for creating a workpad."""

    title: str = Field(..., min_length=1, max_length=100)


class RunTestsRequest(BaseModel):
    """Request body for triggering a test run."""

    target: str = Field("fast", pattern="^(fast|full)$")
    parallel: bool = True


class RepositoryCreateRequest(BaseModel):
    """Request body for creating or importing a repository."""

    source: Literal["empty", "git", "zip"]
    name: Optional[str] = None
    target_path: Optional[str] = None
    git_url: Optional[str] = None
    zip_base64: Optional[str] = None


class CommitMessageRequestModel(BaseModel):
    """Request for commit message generation."""

    conventional: bool = True


class CheckpointRequest(BaseModel):
    """Request body for checkpointing a workpad."""

    message: str = Field(..., min_length=1)


@app.get("/health", tags=["system"])
async def health() -> Dict[str, str]:
    """Return health status."""

    return {"status": "ok"}


@app.get("/state/global", tags=["state"])
async def global_state() -> Dict[str, Any]:
    """Return the global Solo Git state snapshot."""

    return service.get_global_state()


@app.get("/repos", tags=["repositories"])
async def list_repositories() -> Dict[str, Any]:
    """List repositories managed by Solo Git."""

    return {"repositories": service.list_repositories(include_state=True)}


@app.post("/repos", tags=["repositories"], status_code=status.HTTP_201_CREATED)
async def create_repository(request: RepositoryCreateRequest) -> Dict[str, Any]:
    """Create or import a repository."""

    try:
        target_path = Path(request.target_path).expanduser() if request.target_path else None
        if request.source == "empty":
            return service.initialize_repository(
                empty=True,
                name=request.name,
                target_path=target_path,
            )
        if request.source == "git":
            if not request.git_url:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="git_url is required")
            return service.initialize_repository(
                git_url=request.git_url,
                name=request.name,
            )
        if request.source == "zip":
            if not request.zip_base64:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="zip_base64 is required")
            try:
                zip_bytes = base64.b64decode(request.zip_base64)
            except binascii.Error as exc:  # pragma: no cover - invalid base64
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid zip_base64 payload") from exc
            return service.initialize_repository(
                zip_bytes=zip_bytes,
                name=request.name,
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported source type")
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/repos/{repo_id}", tags=["repositories"])
async def get_repository(repo_id: str) -> Dict[str, Any]:
    """Retrieve repository details."""

    repo = service.get_repository(repo_id, include_state=True)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")
    return repo


@app.get("/repos/{repo_id}/workpads", tags=["workpads"])
async def list_workpads(repo_id: str) -> Dict[str, Any]:
    """List workpads for a repository."""

    repo = service.get_repository(repo_id, include_state=True)
    if not repo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found")

    workpads = service.list_workpads(repo_id)
    return {"repository": repo_id, "workpads": workpads}


@app.post("/repos/{repo_id}/workpads", tags=["workpads"], status_code=status.HTTP_201_CREATED)
async def create_workpad(repo_id: str, request: WorkpadCreateRequest) -> Dict[str, Any]:
    """Create a new workpad for a repository."""

    try:
        workpad = service.create_workpad(repo_id, request.title)
        return workpad
    except GitEngineError as exc:  # pragma: no cover - FastAPI handles error mapping
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/workpads/{pad_id}/tests", tags=["tests"], status_code=status.HTTP_202_ACCEPTED)
async def run_tests(pad_id: str, request: RunTestsRequest) -> Dict[str, Any]:
    """Execute tests for a workpad."""

    try:
        outcome = await service.run_tests(pad_id, target=request.target, parallel=request.parallel)
    except WorkpadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except (GitEngineError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return outcome.to_dict()


@app.get("/workpads/{pad_id}", tags=["workpads"])
async def get_workpad(pad_id: str) -> Dict[str, Any]:
    """Return details for a specific workpad."""

    workpad = service.get_workpad(pad_id)
    if not workpad:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workpad not found")
    return workpad


@app.delete("/workpads/{pad_id}", tags=["workpads"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_workpad(pad_id: str, force: bool = False) -> None:
    """Delete a workpad."""

    try:
        service.delete_workpad(pad_id, force=force)
    except WorkpadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/workpads/{pad_id}/diff", tags=["workpads"])
async def workpad_diff(pad_id: str) -> Dict[str, Any]:
    """Return diff data for a workpad."""

    try:
        return service.get_workpad_diff(pad_id)
    except WorkpadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.get("/workpads/{pad_id}/promotion", tags=["workpads"])
async def workpad_promotion_status(pad_id: str) -> Dict[str, Any]:
    """Return promotion eligibility for a workpad."""

    try:
        can_promote = service.can_promote(pad_id)
        return {"workpad_id": pad_id, "can_promote": can_promote}
    except WorkpadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/workpads/{pad_id}/promote", tags=["workpads"], status_code=status.HTTP_200_OK)
async def promote_workpad(pad_id: str) -> Dict[str, Any]:
    """Promote a workpad via the service."""

    try:
        return service.promote_workpad(pad_id)
    except WorkpadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/workpads/{pad_id}/commit-message", tags=["workpads"], status_code=status.HTTP_200_OK)
async def generate_commit_message(pad_id: str, request: CommitMessageRequestModel) -> Dict[str, Any]:
    """Generate commit message for a workpad."""

    try:
        return await service.generate_commit_message(pad_id, conventional=request.conventional)
    except WorkpadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.post("/workpads/{pad_id}/checkpoint", tags=["workpads"], status_code=status.HTTP_200_OK)
async def checkpoint_workpad(pad_id: str, request: CheckpointRequest) -> Dict[str, Any]:
    """Checkpoint a workpad with a commit message."""

    try:
        return service.checkpoint_workpad(pad_id, request.message)
    except WorkpadNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@app.delete("/repos/{repo_id}", tags=["repositories"], status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(repo_id: str, keep_files: bool = False) -> None:
    """Delete a repository and optionally retain its files on disk."""

    try:
        service.delete_repository(repo_id, keep_files=keep_files or False)
    except GitEngineError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@app.get("/telemetry/ai", tags=["telemetry"])
async def telemetry_summary(days: int = Query(default=30, ge=1, le=365)) -> Dict[str, Any]:
    """Return AI telemetry summary."""

    try:
        return service.get_telemetry_summary(days=days)
    except Exception as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


__all__ = ["app", "service"]
