from enum import StrEnum


class FailureStage(StrEnum):
    TRANSFORMATION = "transformation"
    VALIDATION = "validation"
    SERIALIZATION = "serialization"
    UPLOAD = "upload"


class ErrorCode(StrEnum):
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_TYPE = "invalid_type"
    INVALID_DATETIME = "invalid_datetime"
    INVALID_GEOMETRY = "invalid_geometry"

    UNKNOWN_MAINDATA_VALUE = "unknown_maindata_value"
    SIGNAL_NOT_FOUND = "signal_not_found"
    TEMPLATE_NOT_FOUND = "template_not_found"

    DMD_REJECTED_ASSET = "dmd_rejected_asset"
    UPLOAD_RETRIES_EXHAUSTED = "upload_retries_exhausted"