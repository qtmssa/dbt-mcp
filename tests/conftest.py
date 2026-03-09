import os
import shutil
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

# During tests, avoid executing the real `dbt` executable (which in CI/tests
# may be a placeholder file). Force the detection routine to a deterministic
# value so tests don't fail due to Exec format errors.
try:
    # import the module and replace the function with a stub that always
    # returns BinaryType.FUSION
    from dbt_mcp.dbt_cli import binary_type as _binary_type

    def _detect_binary_type_stub(file_path: str):
        return _binary_type.BinaryType.FUSION

    _binary_type.detect_binary_type = _detect_binary_type_stub
except Exception:
    # If importing the module fails for some reason in certain test environments,
    # don't raise here — the tests will surface the import problem separately.
    pass

from tests.env_vars import get_env_value


@pytest.fixture
def env_setup(tmp_path: Path, monkeypatch):
    """
    Returns a helper that creates a temporary project layout and applies env vars.
    Needed so the MCP doesn't auto-disable tools due to bad validations.

    Usage:
        project_dir, helpers = env_setup()
        project_dir, helpers = env_setup(env_vars={"DBT_HOST": "host"}, files={"models/foo.sql": "select 1"})
        # or:
        project_dir, helpers = env_setup()
        helpers.set_env({"DBT_HOST": "host"})
        helpers.write_file("models/foo.sql", "select 1")

    The monkeypatch ensures env vars are removed at test teardown.
    """

    @contextmanager
    def _make(
        env_vars: dict[str, str] | None = None, files: dict[str, str] | None = None
    ):
        override_root_dir = (env_vars or {}).get("DBT_PROJECT_ROOT_DIR")
        root_dir_value = override_root_dir or get_env_value("DBT_PROJECT_ROOT_DIR")
        root_dir = Path(root_dir_value) if root_dir_value else (tmp_path / "projects")
        root_dir.mkdir(parents=True, exist_ok=True)
        project_name = f"test_project_{tmp_path.name}"
        project_dir = root_dir / project_name
        project_dir.mkdir(parents=True, exist_ok=True)

        dbt_path_value = get_env_value("DBT_PATH", "dbt")
        mf_path_value = get_env_value("MF_PATH", "mf")
        path_plus_tmp_path = os.environ.get("PATH", "")
        created_fake_binaries = []
        if dbt_path_value == "dbt" or mf_path_value == "mf":
            # a placeholder dbt/mf file if PATH lookup is needed
            dbt_path = tmp_path / "dbt"
            mf_path = tmp_path / "mf"
            dbt_path.touch()
            mf_path.touch()
            created_fake_binaries.extend([dbt_path, mf_path])
            try:
                dbt_path.chmod(0o755)
                mf_path.chmod(0o755)
            except Exception:
                pass
            path_plus_tmp_path = path_plus_tmp_path + os.pathsep + str(tmp_path)

        default_env_vars = {
            "DBT_PROJECT_ROOT_DIR": str(root_dir),
            "DBT_PATH": dbt_path_value,
            "MF_PATH": mf_path_value,
            "PATH": path_plus_tmp_path,
            "DBT_HOST": get_env_value("DBT_HOST", "http://localhost:8000"),
        }

        # Clear env vars that might interfere with tests from the user's environment
        # Save original values so we can restore them after the test
        env_vars_to_clear = [
            "FASTMCP_HOST",
            "FASTMCP_PORT",
            "MCP_TRANSPORT",
            "DBT_MCP_API_KEY",
            "DBT_MCP_ENABLE_TOOLS",
            "DBT_MCP_ENABLE_METRICFLOW_CLI",
            "DBT_MCP_ENABLE_METRICFLOW_PROJECT_FILES",
            "DISABLE_TOOLS",
            "DISABLE_METRICFLOW_CLI",
            "DISABLE_METRICFLOW_PROJECT_FILES",
        ]
        original_values = {k: os.environ.get(k) for k in env_vars_to_clear}
        for var_to_clear in env_vars_to_clear:
            os.environ.pop(var_to_clear, None)

        env_vars = default_env_vars | (env_vars or {})

        class Helpers:
            @staticmethod
            def set_env(mapping: dict[str, str]):
                for k, v in mapping.items():
                    monkeypatch.setenv(k, v)

            @staticmethod
            def unset_env(*names: str):
                for n in names:
                    # ensure removal; monkeypatch doesn't have a direct unset method but setenv(None) isn't supported
                    # so set to empty string or use patch.dict in tests if they need `clear=True`.
                    monkeypatch.delenv(n, raising=False)

            @staticmethod
            def write_file(relpath: str, content: str):
                p = project_dir / relpath
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(content)
                return p

            @staticmethod
            def path(relpath: str):
                return project_dir / relpath

        helpers = Helpers()

        helpers.set_env(env_vars)

        if files:
            for rel, content in files.items():
                helpers.write_file(rel, content)
        try:
            yield project_dir, helpers
        finally:
            # in case multiple tests are run in the same context
            helpers.unset_env(*env_vars.keys())
            # Restore any env vars we cleared at the start
            for k, v in original_values.items():
                if v is not None:
                    os.environ[k] = v
            shutil.rmtree(project_dir, ignore_errors=True)
            for fake_bin in created_fake_binaries:
                fake_bin.unlink(missing_ok=True)

    yield _make


class MockFastMCP:
    def __init__(self):
        self.tools = {}

    def add_tool(self, fn: Callable[..., Any], **kwargs):
        self.tools[fn.__name__] = fn

    def tool(self, **kwargs):
        def decorator(func):
            self.add_tool(func, **kwargs)
            return func

        return decorator


@pytest.fixture
def mock_fastmcp():
    fastmcp = MockFastMCP()
    return fastmcp, fastmcp.tools


@pytest.fixture
def project_root_dir():
    root_dir_value = get_env_value("DBT_PROJECT_ROOT_DIR", "tests")
    root_dir = Path(root_dir_value)
    root_dir.mkdir(parents=True, exist_ok=True)
    return root_dir


@pytest.fixture
def project_path(tmp_path: Path, project_root_dir: Path):
    project_name = f"test_project_{tmp_path.name}"
    project_dir = project_root_dir / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    try:
        yield project_name
    finally:
        shutil.rmtree(project_dir, ignore_errors=True)
