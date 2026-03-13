import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from dbt_mcp.errors import BinaryExecutionError


def _load_binary_type_module():
    module_path = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "dbt_mcp"
        / "dbt_cli"
        / "binary_type.py"
    )
    spec = importlib.util.spec_from_file_location(
        "test_binary_type_module",
        module_path,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_detect_binary_type_runs_help_and_detects_dbt_core():
    module = _load_binary_type_module()

    with (
        patch.object(module.shutil, "which", return_value="dbt"),
        patch.object(
            module.subprocess,
            "run",
            return_value=Mock(
                returncode=0,
                stdout="Usage: dbt [OPTIONS] COMMAND [ARGS]...\n",
                stderr="",
            ),
        ) as mock_run,
    ):
        binary_type = module.detect_binary_type("dbt")

    mock_run.assert_called_once_with(
        ["dbt", "--help"],
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert binary_type == module.BinaryType.DBT_CORE


def test_detect_binary_type_raises_when_help_command_fails():
    module = _load_binary_type_module()

    with (
        patch.object(module.shutil, "which", return_value="dbt"),
        patch.object(
            module.subprocess,
            "run",
            return_value=Mock(returncode=3, stdout="", stderr="bad help"),
        ),
    ):
        with pytest.raises(
            BinaryExecutionError,
            match=r"Cannot execute binary dbt: --help exited with code 3: bad help",
        ):
            module.detect_binary_type("dbt")
