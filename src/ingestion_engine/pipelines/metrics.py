from dataclasses import dataclass


@dataclass
class TemplateCounts:
    """Tracks how many records were written vs quarantined for a single template."""

    written: int = 0
    quarantined: int = 0

    def add_written(self, count: int = 1) -> None:
        self.written += count

    def add_quarantined(self, count: int = 1) -> None:
        self.quarantined += count

    @property
    def total(self) -> int:
        return self.written + self.quarantined

    @property
    def quarantine_ratio(self) -> float:
        return self.quarantined / self.total if self.total else 0.0

    def exceeds_threshold(self, threshold: float) -> bool:
        return self.total > 0 and self.quarantine_ratio > threshold
