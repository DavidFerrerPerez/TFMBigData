from datetime import datetime


def run_id_to_path(run_id: str) -> str:
    """
    Convert an Airflow run ID or ISO datetime-like identifier into a
    filesystem/blob-path-safe ISO representation.
    """
    return datetime.fromisoformat(run_id).strftime("%Y%m%dT%H%M%S.%f")