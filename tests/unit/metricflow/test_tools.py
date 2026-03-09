import subprocess

import pytest
from pytest import MonkeyPatch

from dbt_mcp.metricflow.tools import register_metricflow_tools
from tests.mocks.config import mock_metricflow_config


@pytest.fixture
def mock_process():
    class MockProcess:
        returncode = 0

        def communicate(self, timeout=None):
            return "command output", None

    return MockProcess()


def test_health_checks_command_correctly_formatted(
    monkeypatch: MonkeyPatch, mock_process, mock_fastmcp, project_path
):
    mock_calls = []

    def mock_popen(args, **kwargs):
        mock_calls.append(args)
        return mock_process

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    fastmcp, tools = mock_fastmcp
    register_metricflow_tools(
        fastmcp,
        mock_metricflow_config,
        disabled_tools=set(),
        enabled_tools=None,
        enabled_toolsets=set(),
        disabled_toolsets=set(),
    )
    health_tool = tools["health_checks"]

    health_tool(project_path=project_path, extra_args=None)

    assert mock_calls
    assert mock_calls[0] == [mock_metricflow_config.mf_path, "health-checks"]


def test_list_command_with_extra_args(
    monkeypatch: MonkeyPatch, mock_process, mock_fastmcp, project_path
):
    mock_calls = []

    def mock_popen(args, **kwargs):
        mock_calls.append(args)
        return mock_process

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    fastmcp, tools = mock_fastmcp
    register_metricflow_tools(
        fastmcp,
        mock_metricflow_config,
        disabled_tools=set(),
        enabled_tools=None,
        enabled_toolsets=set(),
        disabled_toolsets=set(),
    )
    list_tool = tools["mf_list"]

    list_tool(project_path=project_path, extra_args=["--foo", "bar"])

    assert mock_calls
    assert mock_calls[0] == [
        mock_metricflow_config.mf_path,
        "list",
        "--foo",
        "bar",
    ]


def test_metricflow_timeout_handling(
    monkeypatch: MonkeyPatch, mock_fastmcp, project_path
):
    class MockProcessWithTimeout:
        def communicate(self, timeout=None):
            raise subprocess.TimeoutExpired(cmd=["mf", "list"], timeout=10)

    def mock_popen(*args, **kwargs):
        return MockProcessWithTimeout()

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    fastmcp, tools = mock_fastmcp
    register_metricflow_tools(
        fastmcp,
        mock_metricflow_config,
        disabled_tools=set(),
        enabled_tools=None,
        enabled_toolsets=set(),
        disabled_toolsets=set(),
    )
    list_tool = tools["mf_list"]

    result = list_tool(project_path=project_path, extra_args=None)
    assert "Timeout: mf command took longer than" in result


def test_metricflow_error_handling(
    monkeypatch: MonkeyPatch, mock_fastmcp, project_path
):
    class MockProcessWithError:
        returncode = 1

        def communicate(self, timeout=None):
            return "error output", None

    def mock_popen(*args, **kwargs):
        return MockProcessWithError()

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    fastmcp, tools = mock_fastmcp
    register_metricflow_tools(
        fastmcp,
        mock_metricflow_config,
        disabled_tools=set(),
        enabled_tools=None,
        enabled_toolsets=set(),
        disabled_toolsets=set(),
    )
    query_tool = tools["query"]

    result = query_tool(project_path=project_path, extra_args=None)
    assert "Error running mf command: error output" in result


def test_execute_mf_cmd_passes_args(
    monkeypatch: MonkeyPatch, mock_process, mock_fastmcp, project_path
):
    mock_calls = []

    def mock_popen(args, **kwargs):
        mock_calls.append(args)
        return mock_process

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    fastmcp, tools = mock_fastmcp
    register_metricflow_tools(
        fastmcp,
        mock_metricflow_config,
        disabled_tools=set(),
        enabled_tools=None,
        enabled_toolsets=set(),
        disabled_toolsets=set(),
    )
    execute_tool = tools["execute_mf_cmd"]

    execute_tool(project_path=project_path, command_args=["list", "--foo", "bar"])

    assert mock_calls
    assert mock_calls[0] == [
        mock_metricflow_config.mf_path,
        "list",
        "--foo",
        "bar",
    ]
