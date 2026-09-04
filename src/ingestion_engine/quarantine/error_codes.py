from enum import StrEnum


class FailureStage(StrEnum):
    STANDARDIZATION = "standardization"
    SERIALIZATION = "serialization"
    UPLOAD = "upload"


class ErrorCode(StrEnum):
    REQUIRED_FIELD_MISSING = "required_field_missing"
    INVALID_TYPE = "invalid_type"
    INVALID_GEOMETRY = "invalid_geometry"
    DUPLICATED_ID = "duplicated_id"

    DMD_REJECTED_ASSET = "dmd_rejected_asset"