"""Changes API endpoint."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from api.auth import verify_api_key
from api.dependencies import get_change_repository
from api.schemas.books import ChangeResponse, PaginatedResponse
from database.repositories.change_repository import ChangeRepository

router = APIRouter(prefix="/changes", tags=["changes"])


@router.get("", response_model=PaginatedResponse[ChangeResponse])
async def get_changes(
    since: Optional[str] = Query(None, description="Filter changes since ISO datetime"),
    change_type: Optional[str] = Query(None, description="Filter by change type"),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    page: int = Query(1, ge=1, description="Page number"),
    api_key: str = Depends(verify_api_key),
    change_repo: ChangeRepository = Depends(get_change_repository)
):
    """
    Get recent changes with filtering.

    Args:
        since: Filter changes since this datetime (ISO format)
        change_type: Filter by change type
        limit: Items per page
        page: Page number
        api_key: API key (from dependency)
        change_repo: Change repository (from dependency)

    Returns:
        Paginated list of changes
    """
    # Parse since datetime
    since_dt = None
    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
        except ValueError:
            since_dt = None

    # Fetch changes
    changes = await change_repo.get_recent_changes(since=since_dt, limit=limit * page)

    # Filter by change type if specified
    if change_type:
        changes = [c for c in changes if c.change_type == change_type]

    # Paginate
    skip = (page - 1) * limit
    paginated_changes = changes[skip:skip + limit]

    # Convert to response models
    change_responses = [
        ChangeResponse(
            id=str(change._id),
            book_id=str(change.book_id),
            book_name=change.book_name,
            change_type=change.change_type,
            field_name=change.field_name,
            old_value=change.old_value,
            new_value=change.new_value,
            detected_at=change.detected_at
        )
        for change in paginated_changes
    ]

    total = len(changes)
    return PaginatedResponse.create(change_responses, total, page, limit)

