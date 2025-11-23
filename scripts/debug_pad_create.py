# From repo root
powershell -ExecutionPolicy Bypass -File scripts\build_sidecar.ps1import tempfile
from pathlib import Path
from click.testing import CliRunner
from sologit.cli.main import cli
from sologit.state.manager import StateManager


def main():
    sd = tempfile.mkdtemp(prefix='sologit_state_')
    dd = tempfile.mkdtemp(prefix='sologit_data_')
    rd = tempfile.mkdtemp(prefix='test_repo_')

    runner = CliRunner(env={
        'SOLOGIT_STATE_PATH': sd,
        'SOLOGIT_DATA_PATH': dd,
    })

    res = runner.invoke(cli, ['repo','init','--path', rd, '--name','test-repo','--empty'])
    print('repo init exit:', res.exit_code)
    print(res.output)

    sm = StateManager(state_dir=Path(sd))
    repos = sm.list_repositories()
    rid = repos[0].repo_id if repos else None
    print('repo id:', rid)

    res2 = runner.invoke(cli, ['pad','create','conventional-test','--repo', rid])
    print('pad create exit:', res2.exit_code)
    print(res2.output)
    print('exception:', repr(res2.exception))


if __name__ == '__main__':
    main()
