from datetime import datetime

def run_id_to_path(run_id: str) -> str:
    """
    Convert an Airflow run ID into a filesystem/blob-path-safe ISO representation.
    """

    try:
        iso_part = run_id.replace("manual__", "").split("+")[0]
        dt = datetime.fromisoformat(iso_part)
        return dt.strftime("%Y%m%dT%H%M%S.%f") + "Z"
    except ValueError:
        return run_id