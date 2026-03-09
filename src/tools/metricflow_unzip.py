from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import ZipFile


@dataclass(frozen=True)
class UnzipResult:
    """解压结果。

    Args:
        extract_root: 解压输出目录。
        project_root: MetricFlow 工程根目录。
    """

    extract_root: Path
    project_root: Path


def _validate_metricflow_root(root: Path) -> None:
    missing = []
    if not (root / "dbt_project.yml").exists():
        missing.append("dbt_project.yml")
    if not (root / "profiles.yml").exists():
        missing.append("profiles.yml")
    if not (root / "models").exists():
        missing.append("models/")
    if missing:
        raise ValueError(
            "MetricFlow 工程不完整，缺少: " + ", ".join(missing) + f"（根目录: {root}）"
        )


def _safe_extract(zip_path: Path, target: Path) -> None:
    with ZipFile(zip_path, "r") as zip_ref:
        target_resolved = target.resolve()
        for member in zip_ref.infolist():
            member_path = (target / member.filename).resolve()
            if not member_path.is_relative_to(target_resolved):
                raise ValueError("ZIP 路径不安全。")
        zip_ref.extractall(target)


def _resolve_input_root(root: Path) -> Path:
    entries = [p for p in root.iterdir() if not p.name.startswith("__MACOSX")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return root


def unzip_metricflow_zip(zip_path: str | Path, extract_root: str | Path) -> UnzipResult:
    """解压 MetricFlow ZIP 并解析工程根目录。

    Args:
        zip_path: ZIP 文件路径。
        extract_root: 解压输出目录。

    Returns:
        UnzipResult: 解压结果。
    """

    zip_file = Path(zip_path).resolve()
    target = Path(extract_root).resolve()
    if not zip_file.exists():
        raise ValueError(f"ZIP 文件不存在: {zip_file}")

    target.mkdir(parents=True, exist_ok=True)
    _safe_extract(zip_file, target)
    project_root = _resolve_input_root(target)
    _validate_metricflow_root(project_root)
    return UnzipResult(extract_root=target, project_root=project_root)


def main() -> None:
    """CLI 入口，用于 Claude Code skill scripts 调用。

    Args:
        --zip: ZIP 文件路径。
        --output: 解压输出目录。
    """

    import argparse

    parser = argparse.ArgumentParser(description="Unzip MetricFlow ZIP")
    parser.add_argument("--zip", required=True, help="ZIP 文件路径")
    parser.add_argument("--output", required=True, help="解压输出目录")
    args = parser.parse_args()

    result = unzip_metricflow_zip(args.zip, args.output)
    print(str(result.project_root))


if __name__ == "__main__":
    main()
