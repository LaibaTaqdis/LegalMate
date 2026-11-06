"""Document upload and analysis arrive in Phase 5. Until then the routes answer clearly instead of pretending."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import current_user
from ..errors import ApiError

router = APIRouter(tags=["documents"])


def _soon():
    return ApiError(501, "NOT_IMPLEMENTED", "Document upload is not available yet. For now, type or paste the part of the document you need help with.")


@router.post("/documents")
def upload_document(_: dict = Depends(current_user)):
    raise _soon()


@router.post("/analyses")
def create_analysis(_: dict = Depends(current_user)):
    raise _soon()
