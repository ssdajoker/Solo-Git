
from click.testing import CliRunner
from sologit.cli.main import cli

def test_repo_list_help():
    runner = CliRunner()
    result = runner.invoke(cli, ['repo', 'list', '--help'])
    assert result.exit_code == 0
    assert "List registered repositories" in result.output
