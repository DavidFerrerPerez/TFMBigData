from ingestion_engine.quarantine.error_codes import ErrorCode, FailureStage
from ingestion_engine.quarantine.models import QuarantineRecord


def build_quarantine_records_from_df(df, run_id: str, environment: str, template: str, stage: FailureStage, error_code: ErrorCode, error_message: str):
    """
    Build a list of QuarantineRecord instances from a DataFrame.

    Args:
        df: The DataFrame containing the data.
        run_id (str): The run ID.
        environment (str): The environment identifier.
        template (str): The template code.
        stage (FailureStage): The failure stage.
        error_code (ErrorCode): The error code.
        error_message (str): The error message.

    Returns:
        list[QuarantineRecord]: A list of QuarantineRecord instances.
    """
    records = []

    for row in df.toLocalIterator():
        payload = row.asDict(recursive=True)

        error_code_value = payload.pop("_quarantine_error_code", error_code.value)
        error_message_value = payload.pop("_quarantine_error_message", error_message)
        field_name = payload.pop("_quarantine_field", None)

        records.append(
            QuarantineRecord(
                run_id=run_id,
                environment=environment,
                template_code=template,
                source_id=str(payload.get("id")) if payload.get("id") is not None else None,
                code_reference=payload.get("codeReference"),
                stage=stage,
                error_code=ErrorCode(error_code_value),
                error_message=error_message_value,
                field_name=field_name,
                asset=payload,
            )
        )

    return records

def build_upload_quarantine_records(asset_list: list[dict], template: str, run_id: str, environment: str, response) -> list[QuarantineRecord]:
    records = []

    for asset in asset_list:
        records.append(
            QuarantineRecord(
                run_id=run_id,
                environment=environment,
                template_code=template,
                code_reference=asset.get("codeReference"),
                stage=FailureStage.UPLOAD,
                error_code=ErrorCode.DMD_REJECTED_ASSET,
                error_message=str(response.text),
                asset=asset,
            )
        )

    return records