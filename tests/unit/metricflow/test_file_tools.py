import uuid
from pathlib import Path

import pytest

from dbt_mcp.config.config import MetricflowConfig
from dbt_mcp.metricflow.tools import register_metricflow_tools
from tools.metricflow_zip import build_metricflow_zip


def _register_tools(mock_fastmcp, project_root: Path):
    config = MetricflowConfig(
        project_root_dir=str(project_root),
        mf_path="mf",
        mf_cli_timeout=10,
    )
    fastmcp, tools = mock_fastmcp
    register_metricflow_tools(
        fastmcp,
        config=config,
        disabled_tools=set(),
        enabled_tools=None,
        enabled_toolsets=set(),
        disabled_toolsets=set(),
    )
    return tools


def test_project_management_tools(tmp_path, mock_fastmcp, project_root_dir):
    project_root = project_root_dir
    tools = _register_tools(mock_fastmcp, project_root)

    source_project = tmp_path / "source_project"
    source_project.mkdir()
    (source_project / "profiles.yml").write_text("profile", encoding="utf-8")
    (source_project / "dbt_project.yml").write_text("name: test", encoding="utf-8")
    (source_project / "models").mkdir()
    (source_project / "models" / "foo.sql").write_text(
        "select 1", encoding="utf-8"
    )

    zip_result = build_metricflow_zip(source_project, tmp_path / "project.zip")
    zip_url = zip_result.zip_path.as_uri()

    project_name = f"project_{uuid.uuid4().hex}"

    assert tools["is_project_exist"](project_path=project_name) is False
    tools["upload_project_zip_url"](
        project_path=project_name,
        zip_url=zip_url,
    )
    assert tools["is_project_exist"](project_path=project_name) is True

    listed = tools["list_projects"](project_path=".")
    assert project_name in listed

    with pytest.raises(ValueError):
        tools["upload_project_zip_url"](
            project_path=project_name,
            zip_url=zip_url,
        )

    delete_result = tools["delete_project"](project_path=project_name)
    assert delete_result["deleted"] == project_name
    assert tools["is_project_exist"](project_path=project_name) is False


def test_upload_project_zip_url_batch(tmp_path, mock_fastmcp, project_root_dir):
    project_root = project_root_dir
    tools = _register_tools(mock_fastmcp, project_root)

    source_project_1 = tmp_path / "source_project_1"
    source_project_1.mkdir()
    (source_project_1 / "profiles.yml").write_text("profile", encoding="utf-8")
    (source_project_1 / "dbt_project.yml").write_text(
        "name: test_1", encoding="utf-8"
    )
    (source_project_1 / "models").mkdir()
    (source_project_1 / "models" / "foo.sql").write_text(
        "select 1", encoding="utf-8"
    )

    source_project_2 = tmp_path / "source_project_2"
    source_project_2.mkdir()
    (source_project_2 / "profiles.yml").write_text("profile", encoding="utf-8")
    (source_project_2 / "dbt_project.yml").write_text(
        "name: test_2", encoding="utf-8"
    )
    (source_project_2 / "models").mkdir()
    (source_project_2 / "models" / "bar.sql").write_text(
        "select 2", encoding="utf-8"
    )

    zip_result_1 = build_metricflow_zip(source_project_1, tmp_path / "project_1.zip")
    zip_result_2 = build_metricflow_zip(source_project_2, tmp_path / "project_2.zip")

    project_name_1 = f"project_{uuid.uuid4().hex}"
    project_name_2 = f"project_{uuid.uuid4().hex}"

    result = tools["upload_project_zip_url"](
        batch=[
            {"project_path": project_name_1, "zip_url": zip_result_1.zip_path.as_uri()},
            {"project_path": project_name_2, "zip_url": zip_result_2.zip_path.as_uri()},
        ]
    )

    assert result["success"] is True
    assert tools["is_project_exist"](project_path=project_name_1) is True
    assert tools["is_project_exist"](project_path=project_name_2) is True
