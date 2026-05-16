"""GET /audit/{query_id} — implemented in TASK-011."""

from fastapi import APIRouter

router = APIRouter(tags=["audit"])
