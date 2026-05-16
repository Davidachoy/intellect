"""Tests for multi-company synthesis."""

from intelligence.synthesize import synthesize_multi_company_response


def test_synthesize_two_companies() -> None:
    text = synthesize_multi_company_response(
        [
            {
                "company_name": "Acme Retail",
                "raw_insights": [
                    {
                        "aggregation": "count",
                        "value": 847,
                        "filters": {"region": "Italy", "status": "active"},
                    }
                ],
                "record_counts": [847],
            },
            {
                "company_name": "NordLogistics",
                "raw_insights": [
                    {
                        "aggregation": "count",
                        "value": 120,
                        "filters": {"region": "Italy"},
                    }
                ],
                "record_counts": [120],
            },
        ]
    )
    assert "Acme Retail" in text
    assert "NordLogistics" in text
    assert "847" in text
