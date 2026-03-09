import os
from contextlib import contextmanager
from pathlib import Path


def load_env_file(path: str | os.PathLike[str] = ".env") -> dict[str, str]:
    """Load a simple .env file into a dict."""
    env: dict[str, str] = {}
    env_path = Path(path)
    if not env_path.exists():
        return env
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


_ENV_FILE_VALUES = load_env_file()


def get_env_value(name: str, default: str | None = None) -> str | None:
    """Get env var from process env or .env file, with fallback."""
    return os.environ.get(name) or _ENV_FILE_VALUES.get(name) or default


@contextmanager
def env_vars_context(env_vars: dict[str, str]):
    """Temporarily set environment variables and restore them afterward."""
    # Store original env vars
    original_env = {}

    # Save original and set new values
    for key, value in env_vars.items():
        if key in os.environ:
            original_env[key] = os.environ[key]
        os.environ[key] = value

    try:
        yield
    finally:
        # Restore original values
        for key in env_vars:
            if key in original_env:
                os.environ[key] = original_env[key]
            else:
                del os.environ[key]


@contextmanager
def default_env_vars_context(override_env_vars: dict[str, str] | None = None):
    with env_vars_context(
        {
            "DBT_HOST": get_env_value("DBT_HOST", "http://localhost:8000"),
            "DBT_PROD_ENV_ID": get_env_value("DBT_PROD_ENV_ID", "1234"),
            "DBT_TOKEN": get_env_value("DBT_TOKEN", "5678"),
            "DBT_PROJECT_ROOT_DIR": get_env_value("DBT_PROJECT_ROOT_DIR", "tests"),
            "DBT_PATH": get_env_value("DBT_PATH", "dbt"),
            "MF_PATH": get_env_value("MF_PATH", "mf"),
            "DBT_DEV_ENV_ID": get_env_value("DBT_DEV_ENV_ID", "5678"),
            "DBT_USER_ID": get_env_value("DBT_USER_ID", "9012"),
            "DBT_CLI_TIMEOUT": get_env_value("DBT_CLI_TIMEOUT", "10"),
            "DBT_ACCOUNT_ID": get_env_value("DBT_ACCOUNT_ID", "12345"),
            "DISABLE_TOOLS": "",
            "DISABLE_DBT_CODEGEN": "false",
        }
        | (override_env_vars or {})
    ):
        yield
