class PipelineExecutionError(RuntimeError):
    def __init__(self, stage: str, failures: list[str]) -> None:
        self.stage = stage
        self.failures = failures
        details = " | ".join(failures)
        super().__init__(f"{stage.capitalize()} pipeline failed for {len(failures)} item(s): {details}")


class QuarantineThresholdExceededError(RuntimeError):
    """Raised when a template's quarantine ratio exceeds the configured threshold."""

    def __init__(self, template: str, quarantined: int, total: int, threshold: float) -> None:
        self.template = template
        self.quarantined = quarantined
        self.total = total
        self.threshold = threshold
        ratio = quarantined / total if total else 0.0
        super().__init__(
            f"Template '{template}' quarantine ratio {ratio:.2%} ({quarantined}/{total}) "
            f"exceeds the allowed threshold of {threshold:.2%}."
        )