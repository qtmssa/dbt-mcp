从一个或多个 URL 下载 dbt 项目 ZIP 并解压到 `DBT_PROJECT_ROOT_DIR` 下的指定子目录。支持单个上传（`project_path` + `zip_url`）或批量上传（`batch`）。不会覆盖已存在的项目目录；若目标已存在会返回错误。可用于远程模式下先上传项目文件。
