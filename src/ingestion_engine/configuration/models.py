from pydantic import BaseModel, Field


class SourceConfig(BaseModel):
    schema_name: str = Field(alias="schema")

class BlobPathConfig(BaseModel):
    raw: str
    unified: str
    standard: str

class StorageConfig(BaseModel):
    container: str
    paths: BlobPathConfig

class IngestionConfig(BaseModel):
    source: SourceConfig
    tables: list[str]
    storage: StorageConfig
