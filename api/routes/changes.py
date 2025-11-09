"""Changes API endpoint."""

from fastapi import APIRouter, Depends

from api.auth import verify_api_key
from api.dependencies import get_change_repository
from api.schemas.books import ChangeResponse, PaginatedResponse
from api.schemas.common import ChangeFilters
from database.repositories.change_repository import ChangeRepository

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("", response_model=PaginatedResponse[ChangeResponse])
async def get_changes(
    filters: ChangeFilters = Depends(),
    api_key: str = Depends(verify_api_key),
    change_repo: ChangeRepository = Depends(get_change_repository)
):
    """
    Get recent changes with filtering.

    Args:
        filters: Query parameter model for filtering/pagination.
        api_key: API key (from dependency).
        change_repo: Change repository (from dependency).

    Returns:
        Paginated list of changes.
    """
    change_type_value = (
        filters.change_type.value if filters.change_type is not None else None
    )

    skip = (filters.page - 1) * filters.limit

    changes = await change_repo.get_recent_changes(
        since=filters.since,
        change_type=change_type_value,
        skip=skip,
        limit=filters.limit
    )

    total = await change_repo.count_recent_changes(
        since=filters.since,
        change_type=change_type_value
    )

    change_responses = [
        ChangeResponse(
            id=str(change.id) if change.id else "",
            book_id=str(change.book_id),
            book_name=change.book_name,
            change_type=change.change_type,
            field_name=change.field_name,
            old_value=change.old_value,
            new_value=change.new_value,
            detected_at=change.detected_at
        )
        for change in changes
    ]

    return PaginatedResponse.create(
        change_responses,
        total,
        filters.page,
        filters.limit
    )

