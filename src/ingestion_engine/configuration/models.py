from pydantic import BaseModel

class DataQualityConfig(BaseModel):
    core_fields: list[str]
    non_null_fields: list[str]
    id_column: str
    geometry_column: str

class SourceConfig(BaseModel):
    db_schema: str

class BlobPathConfig(BaseModel):
    raw: str
    standard: str
    quarantine: str

class StorageConfig(BaseModel):
    container: str
    paths: BlobPathConfig

class AnonymizationConfig(BaseModel):
    text_columns: list[str]
    geometry_columns: list[str]

class DMDConfig(BaseModel):
    asset_name_prefix: str
    code_reference_prefix: str
    origin_id: int
    consumer_application_id: int
    main_hierarchy_parent: int
    batch_size: int

class QualityThresholdConfig(BaseModel):
    max_quarantine_ratio: float

class IngestionConfig(BaseModel):
    available_environments: list[str]
    source: SourceConfig
    templates: list[str]
    storage: StorageConfig
    data_quality: DataQualityConfig
    anonymization: AnonymizationConfig
    dmd: DMDConfig
    quality_threshold: QualityThresholdConfig


