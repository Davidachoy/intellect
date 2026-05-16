"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from middleware.auth import AuthenticatedCompany, resolve_company_by_api_key
from shared.models.query import QueryRequest


async def get_authenticated_company(
    body: QueryRequest,
) -> AuthenticatedCompany:
    row = await resolve_company_by_api_key(body.querier_api_key)
    return AuthenticatedCompany(
        company_id=UUID(str(row["id"])),
        name=str(row["name"]),
        api_key_hash=str(row["api_key_hash"]),
    )


AuthenticatedCompanyDep = Annotated[AuthenticatedCompany, Depends(get_authenticated_company)]
