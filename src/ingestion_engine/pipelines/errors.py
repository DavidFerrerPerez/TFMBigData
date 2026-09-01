class PipelineExecutionError(RuntimeError):
    def __init__(self, stage: str, failures: list[str]) -> None:
        self.stage = stage
        self.failures = failures
        details = " | ".join(failures)
        super().__init__(f"{stage.capitalize()} pipeline failed for {len(failures)} item(s): {details}")