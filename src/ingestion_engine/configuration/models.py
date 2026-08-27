from pydantic import BaseModel, Field

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

class StorageConfig(BaseModel):
    container: str
    paths: BlobPathConfig

class AnonymizationConfig(BaseModel):
    text_columns: list[str]
    geometry_columns: list[str]

class IngestionConfig(BaseModel):
    available_environments: list[str]
    source: SourceConfig
    templates: list[str]
    storage: StorageConfig
    data_quality: DataQualityConfig
    anonymization: AnonymizationConfig
    main_hierarchy_parent: int
