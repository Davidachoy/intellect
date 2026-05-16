"""Intelligence fan-out plan tests."""

from __future__ import annotations

import sys
from pathlib import Path

_AGENTS_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _AGENTS_ROOT.parents[1]
for path in (
    str(_REPO_ROOT / "packages" / "shared"),
    str(_REPO_ROOT / "packages"),
    str(_AGENTS_ROOT),
):
    if path not in sys.path:
        sys.path.insert(0, path)

from intelligence.plans import build_intelligence_jobs

ACME_AGENT = "b1000000-0000-4000-8000-000000000001"
NORD_AGENT = "b1000000-0000-4000-8000-000000000002"


def test_compound_compare_one_agent_per_sub_query() -> None:
    raw = (
        "Compare active clients for Acme Retail in Italy with on-time shipment "
        "volume for NordLogistics in Italy."
    )
    structured = {
        "intent": "compare",
        "aggregation": "count",
        "domain": "customers",
        "mentioned_companies": ["Acme Retail", "NordLogistics"],
        "sub_queries": [
            {
                "intent": "count",
                "filters": {"region": "Italy", "status": "active"},
                "aggregation": "count",
                "domain": "customers",
            },
            {
                "intent": "count",
                "filters": {"region": "Italy"},
                "aggregation": "count",
                "domain": "logistics_shipments",
            },
        ],
    }
    jobs = build_intelligence_jobs(
        structured_query=structured,
        target_agent_ids=[ACME_AGENT, NORD_AGENT],
        target_company_id="",
        raw_query=raw,
    )
    assert len(jobs) == 2
    assert jobs[0].agent_id == ACME_AGENT
    assert jobs[1].agent_id == NORD_AGENT
    assert jobs[0].structured_query["domain"] == "customers"
    assert jobs[1].structured_query["domain"] == "logistics_shipments"
