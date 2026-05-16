"""Summarize LangGraph node updates for audit logs and SSE."""

from __future__ import annotations

from typing import Any

NODE_ORDER = (
    "query_router",
    "benchmark",
    "intelligence",
    "explainer",
    "pricing",
    "privacy_guard",
)


def summarize_node_update(node: str, update: dict[str, Any]) -> dict[str, Any]:
    """Return a client-safe payload summary for a completed graph node."""
    if node == "query_router":
        return {
            "structured_query": update.get("structured_query"),
            "target_agent_ids": update.get("target_agent_ids"),
            "model_attribution": (update.get("model_attribution") or {}).get("router"),
        }
    if node == "benchmark":
        return {
            "raw_insights": update.get("raw_insights"),
            "record_counts": update.get("record_counts"),
            "preview": (update.get("response") or "")[:200],
        }
    if node == "intelligence":
        results = update.get("intelligence_results") or []
        if not results and update.get("raw_insights"):
            return {
                "record_counts": update.get("record_counts"),
                "insight_count": len(update.get("raw_insights") or []),
            }
        return {
            "intelligence_results": results,
            "companies": [
                {
                    "company_name": r.get("company_name"),
                    "agent_id": r.get("agent_id"),
                    "record_counts": r.get("record_counts"),
                    "insight_count": len(r.get("raw_insights") or []),
                    "error": r.get("error"),
                }
                for r in results
            ],
            "record_counts": update.get("record_counts"),
            "insight_count": len(update.get("raw_insights") or []),
        }
    if node == "explainer":
        return {
            "explanation": (update.get("explanation") or "")[:500],
            "chars": len(update.get("explanation") or ""),
        }
    if node == "pricing":
        return {
            "cost_usd": update.get("cost_usd"),
            "sensitivity_tier": update.get("sensitivity_tier"),
        }
    if node == "privacy_guard":
        return {
            "passed_privacy": update.get("passed_privacy"),
            "block_reason": update.get("block_reason"),
        }
    return {}


def node_audit_event(node: str, update: dict[str, Any]) -> tuple[str, str]:
    """Map a graph node completion to audit_log (agent, event) pair."""
    if node == "query_router":
        return "query_router", "routed"
    if node == "benchmark":
        return "benchmark", "aggregated"
    if node == "intelligence":
        return "intelligence", "aggregated"
    if node == "explainer":
        return "explainer", "explained"
    if node == "pricing":
        return "pricing", "charged"
    if node == "privacy_guard":
        blocked = not update.get("passed_privacy", True)
        return "privacy_guard", "blocked" if blocked else "approved"
    return node, "completed"
