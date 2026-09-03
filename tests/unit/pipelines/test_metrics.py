from ingestion_engine.pipelines.metrics import TemplateCounts


def test_template_counts_starts_at_zero():
    counts = TemplateCounts()
    assert counts.written == 0
    assert counts.quarantined == 0
    assert counts.total == 0
    assert counts.quarantine_ratio == 0.0


def test_template_counts_add_written_and_quarantined():
    counts = TemplateCounts()
    counts.add_written(4)
    counts.add_quarantined(1)

    assert counts.written == 4
    assert counts.quarantined == 1
    assert counts.total == 5


def test_template_counts_add_defaults_to_one():
    counts = TemplateCounts()
    counts.add_written()
    counts.add_quarantined()

    assert counts.written == 1
    assert counts.quarantined == 1


def test_template_counts_quarantine_ratio():
    counts = TemplateCounts(written=8, quarantined=2)
    assert counts.quarantine_ratio == 0.2


def test_template_counts_exceeds_threshold_when_ratio_is_higher():
    counts = TemplateCounts(written=4, quarantined=6)
    assert counts.exceeds_threshold(0.2) is True


def test_template_counts_does_not_exceed_threshold_when_ratio_is_lower():
    counts = TemplateCounts(written=8, quarantined=2)
    assert counts.exceeds_threshold(0.5) is False


def test_template_counts_does_not_exceed_threshold_when_ratio_equals_threshold():
    counts = TemplateCounts(written=8, quarantined=2)
    assert counts.exceeds_threshold(0.2) is False


def test_template_counts_never_exceeds_threshold_when_total_is_zero():
    counts = TemplateCounts()
    assert counts.exceeds_threshold(0.0) is False
