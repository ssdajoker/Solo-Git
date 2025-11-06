"""HTTP client for the Solo Git headless core service."""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Optional
from urllib.parse import urljoin

import requests


_DEFAULT_BASE_URL = "http://127.0.0.1:1234"


class HeadlessServiceError(RuntimeError):
    """Raised when a headless core request fails."""

    def __init__(self, message: str, *, status: Optional[int] = None, payload: Optional[Any] = None) -> None:
        super().__init__(message)
        self.status = status
        self.payload = payload


@dataclass(frozen=True)
class HeadlessClientConfig:
    """Configuration for connecting to the headless core service."""

    base_url: str
    timeout: float = 30.0


class HeadlessClient:
    """Thin HTTP client that mirrors the Solo Git service API."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        session: Optional[requests.Session] = None,
    ) -> None:
        resolved_url = (base_url or os.getenv("SOLOGIT_HEADLESS_URL") or _DEFAULT_BASE_URL).strip()
        resolved_url = resolved_url[:-1] if resolved_url.endswith("/") else resolved_url
        self.config = HeadlessClientConfig(base_url=resolved_url, timeout=timeout)
        self._session = session or requests.Session()

    # ------------------------------------------------------------------
    # Low-level request helper
    # ------------------------------------------------------------------
    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Mapping[str, Any]] = None,
        headers: Optional[Mapping[str, str]] = None,
    ) -> Any:
        """Send an HTTP request to the headless core."""

        url = urljoin(self.config.base_url + "/", path.lstrip("/"))
        request_headers: MutableMapping[str, str] = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        response = self._session.request(
            method,
            url,
            params=params,
            json=json,
            headers=request_headers,
            timeout=self.config.timeout,
        )

        if response.status_code == 204:
            return None

        content_type = response.headers.get("Content-Type", "")
        text = response.text

        data: Any
        if "json" in content_type.lower() and text:
            try:
                data = response.json()
            except ValueError as exc:  # pragma: no cover - unexpected parsing failure
                raise HeadlessServiceError(
                    "Failed to parse JSON response from headless service",
                    status=response.status_code,
                ) from exc
        else:
            data = text

        if response.ok:
            return data

        detail = self._extract_error_detail(data)
        raise HeadlessServiceError(
            f"Headless request failed ({response.status_code}): {detail}",
            status=response.status_code,
            payload=data,
        )

    @staticmethod
    def _extract_error_detail(data: Any) -> str:
        if isinstance(data, Mapping):
            for key in ("detail", "error", "message"):
                value = data.get(key)
                if isinstance(value, str) and value:
                    return value
        if isinstance(data, str) and data.strip():
            return data.strip()
        return "Unknown error"

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------
    def health(self) -> Dict[str, Any]:
        return self._request("GET", "/health")

    def get_global_state(self) -> Dict[str, Any]:
        return self._request("GET", "/state/global")

    def list_repositories(self) -> Iterable[Dict[str, Any]]:
        payload = self._request("GET", "/repos")
        repositories = payload.get("repositories", []) if isinstance(payload, Mapping) else []
        return repositories

    def get_repository(self, repo_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/repos/{repo_id}")

    def create_repository(
        self,
        *,
        source: str,
        name: Optional[str] = None,
        target_path: Optional[str] = None,
        git_url: Optional[str] = None,
        zip_bytes: Optional[bytes] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"source": source, "name": name, "target_path": target_path}
        if git_url:
            payload["git_url"] = git_url
        if zip_bytes:
            payload["zip_base64"] = base64.b64encode(zip_bytes).decode("ascii")
        return self._request("POST", "/repos", json=payload)

    def delete_repository(self, repo_id: str, *, keep_files: bool = False) -> None:
        params = {"keep_files": str(keep_files).lower()}
        self._request("DELETE", f"/repos/{repo_id}", params=params)

    def list_workpads(self, repo_id: str) -> Iterable[Dict[str, Any]]:
        payload = self._request("GET", f"/repos/{repo_id}/workpads")
        workpads = payload.get("workpads", []) if isinstance(payload, Mapping) else []
        return workpads

    def create_workpad(self, repo_id: str, title: str) -> Dict[str, Any]:
        return self._request("POST", f"/repos/{repo_id}/workpads", json={"title": title})

    def get_workpad(self, pad_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/workpads/{pad_id}")

    def delete_workpad(self, pad_id: str, *, force: bool = False) -> None:
        params = {"force": str(force).lower()}
        self._request("DELETE", f"/workpads/{pad_id}", params=params)

    def get_workpad_diff(self, pad_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/workpads/{pad_id}/diff")

    def get_workpad_promotion(self, pad_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/workpads/{pad_id}/promotion")

    def promote_workpad(self, pad_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/workpads/{pad_id}/promote")

    def generate_commit_message(self, pad_id: str, *, conventional: bool = True) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/workpads/{pad_id}/commit-message",
            json={"conventional": conventional},
        )

    def checkpoint_workpad(self, pad_id: str, message: str) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/workpads/{pad_id}/checkpoint",
            json={"message": message},
        )

    def run_tests(self, pad_id: str, *, target: str = "fast", parallel: bool = True) -> Dict[str, Any]:
        return self._request(
            "POST",
            f"/workpads/{pad_id}/tests",
            json={"target": target, "parallel": parallel},
        )

    def get_telemetry_summary(self, *, days: int = 30) -> Dict[str, Any]:
        return self._request("GET", "/telemetry/ai", params={"days": days})


__all__ = ["HeadlessClient", "HeadlessClientConfig", "HeadlessServiceError"]
