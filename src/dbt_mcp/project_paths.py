from __future__ import annotations

from pathlib import Path


def resolve_project_root(root_dir: str) -> Path:
    """Resolve and validate the project root directory."""
    if root_dir is None or not str(root_dir).strip():
        raise ValueError("DBT_PROJECT_ROOT_DIR environment variable is required.")
    root = Path(root_dir).expanduser()
    if not root.is_absolute():
        root = (Path.cwd() / root).resolve()
    else:
        root = root.resolve()
    if not root.exists():
        raise ValueError(f"DBT_PROJECT_ROOT_DIR does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"DBT_PROJECT_ROOT_DIR is not a directory: {root}")
    return root


def normalize_project_path(project_path: str, *, allow_empty: bool = False) -> Path:
    """Normalize and validate a relative project path."""
    if project_path is None:
        if allow_empty:
            return Path(".")
        raise ValueError("project_path is required.")
    project_path_str = str(project_path).strip()
    if not project_path_str:
        if allow_empty:
            return Path(".")
        raise ValueError("project_path is required.")
    candidate = Path(project_path_str)
    if candidate.is_absolute():
        raise ValueError("project_path must be relative to DBT_PROJECT_ROOT_DIR.")
    if ".." in candidate.parts:
        raise ValueError("project_path must not contain '..'.")
    return candidate


def resolve_project_dir(
    root_dir: str,
    project_path: str,
    *,
    must_exist: bool = True,
    allow_empty: bool = False,
) -> Path:
    """Resolve a project directory under the project root."""
    root = resolve_project_root(root_dir)
    rel = normalize_project_path(project_path, allow_empty=allow_empty)
    project_dir = (root / rel).resolve()
    if not project_dir.is_relative_to(root):
        raise ValueError("project_path must be within DBT_PROJECT_ROOT_DIR.")
    if must_exist and not project_dir.is_dir():
        raise ValueError(f"Project directory does not exist: {rel.as_posix()}")
    return project_dir
