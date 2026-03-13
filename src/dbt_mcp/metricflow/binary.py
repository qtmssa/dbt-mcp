import os
import shutil
import subprocess

from dbt_mcp.errors import BinaryExecutionError


def resolve_metricflow_binary(file_path: str) -> str:
    executable = shutil.which(file_path)
    if executable:
        return executable

    expanded = os.path.expanduser(file_path)
    if os.path.exists(expanded):
        return expanded

    raise BinaryExecutionError(f"MF_PATH executable can't be found: {file_path}")


def _raise_help_failure(file_path: str, result: subprocess.CompletedProcess[str]) -> None:
    details = (result.stderr or result.stdout or "").strip()
    if details:
        raise BinaryExecutionError(
            f"Cannot execute binary {file_path}: --help exited with code "
            f"{result.returncode}: {details}"
        )
    raise BinaryExecutionError(
        f"Cannot execute binary {file_path}: --help exited with code {result.returncode}"
    )


def validate_metricflow_binary(file_path: str) -> str:
    """
    Validate the MetricFlow binary can be executed by running `--help`.

    Args:
        file_path: Path to the MetricFlow executable.

    Raises:
        BinaryExecutionError: If the binary cannot be executed or accessed.
    """
    try:
        executable = resolve_metricflow_binary(file_path)
        if os.name == "nt" and str(executable).lower().endswith((".cmd", ".bat")):
            args = ["cmd", "/c", executable, "--help"]
        else:
            args = [executable, "--help"]
        result = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            _raise_help_failure(file_path, result)
        return executable
    except Exception as e:
        if isinstance(e, BinaryExecutionError):
            raise
        raise BinaryExecutionError(f"Cannot execute binary {file_path}: {e}") from e
