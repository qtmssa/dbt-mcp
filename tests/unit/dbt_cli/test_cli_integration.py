import shutil
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

from dbt_mcp.dbt_cli.tools import register_dbt_cli_tools
from tests.conftest import MockFastMCP
from tests.mocks.config import mock_config


class TestDbtCliIntegration(unittest.TestCase):
    @patch("subprocess.Popen")
    def test_dbt_command_execution(self, mock_popen):
        """
        Tests the full execution path for dbt commands, ensuring they are properly
        executed with the right arguments.
        """
        # Mock setup
        mock_process = MagicMock()
        mock_process.communicate.return_value = ("command output", None)
        mock_popen.return_value = mock_process

        mock_fastmcp = MockFastMCP()

        # Register the tools
        register_dbt_cli_tools(
            mock_fastmcp,
            mock_config.dbt_cli_config,
            disabled_tools=set(),
            enabled_tools=None,
            enabled_toolsets=set(),
            disabled_toolsets=set(),
        )

        # Ensure project directory exists under the configured root
        root_dir = Path(mock_config.dbt_cli_config.project_root_dir)
        project_path = f"test_project_{uuid.uuid4().hex}"
        project_dir = root_dir / project_path
        project_dir.mkdir(parents=True, exist_ok=True)

        dbt_path = mock_config.dbt_cli_config.dbt_path

        # Test cases for different command types
        test_cases = [
            # Command name, args, expected command list
            ("build", {}, [dbt_path, "--no-use-colors", "build", "--quiet"]),
            (
                "compile",
                {},
                [dbt_path, "--no-use-colors", "compile", "--quiet"],
            ),
            (
                "docs",
                {},
                [dbt_path, "--no-use-colors", "docs", "--quiet", "generate"],
            ),
            (
                "ls",
                {},
                [dbt_path, "--no-use-colors", "list", "--quiet"],
            ),
            ("parse", {}, [dbt_path, "--no-use-colors", "parse", "--quiet"]),
            ("run", {}, [dbt_path, "--no-use-colors", "run", "--quiet"]),
            ("test", {}, [dbt_path, "--no-use-colors", "test", "--quiet"]),
            (
                "show",
                {"sql_query": "SELECT * FROM model"},
                [
                    dbt_path,
                    "--no-use-colors",
                    "show",
                    "--inline",
                    "SELECT * FROM model",
                    "--favor-state",
                    "--output",
                    "json",
                ],
            ),
            (
                "show",
                {"sql_query": "SELECT * FROM model", "limit": 10},
                [
                    dbt_path,
                    "--no-use-colors",
                    "show",
                    "--inline",
                    "SELECT * FROM model",
                    "--favor-state",
                    "--limit",
                    "10",
                    "--output",
                    "json",
                ],
            ),
        ]

        # Run each test case
        for command_name, kwargs, expected_args in test_cases:
            mock_popen.reset_mock()

            # Call the function
            result = mock_fastmcp.tools[command_name](
                project_path=project_path, **kwargs
            )

            # Verify the command was called correctly
            mock_popen.assert_called_once()
            actual_args = mock_popen.call_args.kwargs.get("args")

            num_params = 4

            self.assertEqual(actual_args[:num_params], expected_args[:num_params])

            # Verify correct working directory
            self.assertEqual(
                mock_popen.call_args.kwargs.get("cwd"), str(project_dir)
            )

            # Verify the output is returned correctly
            self.assertEqual(result, "command output")

        shutil.rmtree(project_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
