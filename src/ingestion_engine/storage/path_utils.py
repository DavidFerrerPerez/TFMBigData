def run_id_to_path(run_id: str) -> str:
    """
    Convert an Airflow run ID into a filesystem/blob-path-safe ISO representation.
    """
    return run_id.replace(":", "").replace("-", "")