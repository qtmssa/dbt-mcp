from unittest.mock import Mock, patch

import pytest

from dbt_mcp.errors import BinaryExecutionError
from dbt_mcp.metricflow.binary import resolve_metricflow_binary, validate_metricflow_binary


class TestValidateMetricflowBinary:
    @patch("dbt_mcp.metricflow.binary.shutil.which", return_value="mf")
    @patch("dbt_mcp.metricflow.binary.subprocess.run")
    def test_runs_help_command(self, mock_run, _mock_which):
        mock_run.return_value = Mock(returncode=0, stdout="MetricFlow help", stderr="")

        resolved = validate_metricflow_binary("mf")

        mock_run.assert_called_once_with(
            ["mf", "--help"],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert resolved == "mf"

    @patch("dbt_mcp.metricflow.binary.shutil.which", return_value="mf")
    @patch("dbt_mcp.metricflow.binary.subprocess.run")
    def test_raises_when_binary_cannot_execute(self, mock_run, _mock_which):
        mock_run.side_effect = OSError("boom")

        with pytest.raises(BinaryExecutionError, match="Cannot execute binary mf"):
            validate_metricflow_binary("mf")

    @patch("dbt_mcp.metricflow.binary.shutil.which", return_value="mf")
    @patch("dbt_mcp.metricflow.binary.subprocess.run")
    def test_raises_when_help_command_fails(self, mock_run, _mock_which):
        mock_run.return_value = Mock(returncode=2, stdout="", stderr="help failed")

        with pytest.raises(
            BinaryExecutionError,
            match=r"Cannot execute binary mf: --help exited with code 2: help failed",
        ):
            validate_metricflow_binary("mf")

    @patch("dbt_mcp.metricflow.binary.shutil.which", return_value=None)
    def test_raises_when_metricflow_binary_cannot_be_found(self, _mock_which):
        with pytest.raises(BinaryExecutionError, match="MF_PATH executable can't be found: missing-mf"):
            resolve_metricflow_binary("missing-mf")
