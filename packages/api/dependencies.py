"""Shared FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from fastapi import HTTPException, status

from middleware.auth import AuthenticatedCompany, resolve_company_by_api_key
from shared.models.ingest import IngestRequest
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


async def get_ingest_authenticated_company(
    body: IngestRequest,
) -> AuthenticatedCompany:
    row = await resolve_company_by_api_key(body.owner_api_key)
    company = AuthenticatedCompany(
        company_id=UUID(str(row["id"])),
        name=str(row["name"]),
        api_key_hash=str(row["api_key_hash"]),
    )
    if company.company_id != body.company_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key is not authorized for this company",
        )
    return company


AuthenticatedCompanyDep = Annotated[AuthenticatedCompany, Depends(get_authenticated_company)]
IngestAuthenticatedCompanyDep = Annotated[
    AuthenticatedCompany, Depends(get_ingest_authenticated_company)
]
