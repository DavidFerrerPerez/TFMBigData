from ingestion_engine.pipelines.errors import PipelineExecutionError, QuarantineThresholdExceededError


def test_pipeline_execution_error_message_includes_failures():
    error = PipelineExecutionError("upload", ["template=a: boom"])
    assert "Upload pipeline failed for 1 item(s)" in str(error)
    assert "template=a: boom" in str(error)
    assert error.stage == "upload"
    assert error.failures == ["template=a: boom"]


def test_quarantine_threshold_exceeded_error_message():
    error = QuarantineThresholdExceededError("template_a", quarantined=6, total=10, threshold=0.2)

    assert error.template == "template_a"
    assert error.quarantined == 6
    assert error.total == 10
    assert error.threshold == 0.2
    assert "template_a" in str(error)
    assert "60.00%" in str(error)
    assert "20.00%" in str(error)


def test_quarantine_threshold_exceeded_error_handles_zero_total():
    error = QuarantineThresholdExceededError("template_a", quarantined=0, total=0, threshold=0.2)
    assert "0.00%" in str(error)
