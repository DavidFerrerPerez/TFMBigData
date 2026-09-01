import json
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict
from urllib.parse import quote
from uuid import uuid4

from ingestion_engine.quarantine.models import QuarantineRecord
from ingestion_engine.storage.blob_client import BlobClient
from ingestion_engine.quarantine.models import QuarantineRecord
from dataclasses import asdict
from typing import Iterable
from urllib.parse import quote
from uuid import uuid4
import json
from collections import defaultdict


class QuarantineService:
    """Service responsible for persisting failed assets in the quarantine Azure Blob Storage container."""

    def __init__(self, blob_client: BlobClient, base_path: str = "") -> None:
        self._blob_client = blob_client
        self._base_path = base_path.strip("/")

    @staticmethod
    def _to_dict(record: QuarantineRecord) -> dict:
        data = asdict(record)
        data["stage"] = record.stage.value
        data["error_code"] = record.error_code.value
        data["failed_at"] = record.failed_at.isoformat()
        return data

    @staticmethod
    def _path_value(value: str) -> str:
        return quote(str(value), safe="-_.")

    def _build_blob_prefix(self, record: QuarantineRecord) -> str:
        """Build the blob prefix for a given QuarantineRecord."""
        date = record.failed_at.date().isoformat()
        parts = [
            self._base_path,
            f"environment={self._path_value(record.environment)}",
            f"date={date}",
            f"run_id={self._path_value(record.run_id)}",
            f"template={self._path_value(record.template_code)}",
            f"stage={self._path_value(record.stage.value)}",
        ]
        return "/".join(part for part in parts if part)

    def _group_records(self, records: Iterable[QuarantineRecord]) -> dict[str, list[QuarantineRecord]]:
        """Group QuarantineRecords by their blob prefix."""
        groups: dict[str, list[QuarantineRecord]] = defaultdict(list)
        for record in records:
            groups[self._build_blob_prefix(record)].append(record)
        return dict(groups)

    def _write_group(self, records: list[QuarantineRecord], blob_prefix: str) -> str:
        content = "\n".join(json.dumps(self._to_dict(record), ensure_ascii=False, default=str) for record in records)
        file_name = f"failed_assets_{uuid4()}.jsonl"
        blob_path = f"{blob_prefix}/{file_name}"
        self._blob_client.upload_text(content, blob_path)
        return blob_path

    def write(self, records: Iterable[QuarantineRecord]) -> list[str]:
        records = list(records)
        if not records:
            return []

        groups = self._group_records(records)
        uploaded_paths = []

        for blob_prefix, group_records in groups.items():
            uploaded_paths.append(self._write_group(group_records, blob_prefix))

        return uploaded_paths