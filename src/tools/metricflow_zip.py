from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(frozen=True)
class ZipResult:
    """打包结果。

    Args:
        zip_path: 生成的 ZIP 文件路径。
        size_bytes: ZIP 文件大小（字节）。
        base64_str: ZIP 的 base64 字符串。
    """

    zip_path: Path
    size_bytes: int
    base64_str: str


def _iter_files(root: Path, exclude_dirs: Iterable[str]) -> Iterable[Path]:
    exclude_set = {name.lower() for name in exclude_dirs}
    for path in root.rglob("*"):
        rel_parts = {part.lower() for part in path.relative_to(root).parts}
        if rel_parts & exclude_set:
            continue
        if path.is_file():
            yield path


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


def build_metricflow_zip(
    project_root: str | Path,
    output_zip: str | Path,
    *,
    exclude_dirs: Iterable[str] = ("logs",),
    size_limit_bytes: int = 1024 * 1024 * 1024,
) -> ZipResult:
    """构建 MetricFlow 工程 ZIP。

    Args:
        project_root: MetricFlow 工程根目录。
        output_zip: 输出 ZIP 路径。
        exclude_dirs: 排除目录名（匹配任意层级目录名）。
        size_limit_bytes: ZIP 最大字节数，默认 1GB。

    Returns:
        ZipResult: 打包结果。
    """

    root = Path(project_root).resolve()
    zip_path = Path(output_zip).resolve()
    if not root.exists():
        raise ValueError(f"工程路径不存在: {root}")

    _validate_metricflow_root(root)
    zip_path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for file_path in _iter_files(root, exclude_dirs=exclude_dirs):
            arcname = file_path.relative_to(root).as_posix()
            zip_file.write(file_path, arcname)

    size_bytes = zip_path.stat().st_size
    if size_bytes > size_limit_bytes:
        zip_path.unlink(missing_ok=True)
        raise ValueError(
            f"ZIP 过大: {size_bytes} bytes，限制 {size_limit_bytes} bytes"
        )

    base64_str = base64.b64encode(zip_path.read_bytes()).decode("ascii")
    return ZipResult(zip_path=zip_path, size_bytes=size_bytes, base64_str=base64_str)


def main() -> None:
    """CLI 入口，用于 Claude Code skill scripts 调用。

    Args:
        --project: MetricFlow 工程根目录。
        --output: 输出 ZIP 路径。
    """

    import argparse

    parser = argparse.ArgumentParser(description="Build MetricFlow ZIP (base64 output)")
    parser.add_argument("--project", required=True, help="MetricFlow 工程根目录")
    parser.add_argument("--output", required=True, help="输出 ZIP 路径")
    args = parser.parse_args()

    result = build_metricflow_zip(args.project, args.output)
    print(result.base64_str)


if __name__ == "__main__":
    main()
