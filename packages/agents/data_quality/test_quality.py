from data_quality.checks import run_quality_checks
from data_quality.report import build_report
from shared.models.data_quality import DataQualityRecommendation


def test_reject_low_score_duplicate_and_pii() -> None:
    docs = [
        {"content": "contact john@acme.com", "metadata": {"region": "IT"}},
        {"content": "contact john@acme.com", "metadata": {"region": "US"}},
        {"content": "", "metadata": {}},
    ]
    issues = run_quality_checks(docs)
    report = build_report(issues)
    assert report.score < 60
    assert report.recommendation == DataQualityRecommendation.REJECT


def test_clean_batch_high_score() -> None:
    docs = [
        {"content": "segment enterprise in EMEA", "metadata": {"region": "EMEA", "ltv": 100}},
        {"content": "segment smb in APAC", "metadata": {"region": "APAC", "ltv": 120}},
        {"content": "segment mid in NA", "metadata": {"region": "NA", "ltv": 110}},
    ]
    report = build_report(run_quality_checks(docs))
    assert report.score > 80
    assert report.recommendation == DataQualityRecommendation.INGEST
