from fastapi import APIRouter, Depends
from ..auth import authenticate
from ..db import upsert_developer
from ..schemas import WhoAmIResponse

router = APIRouter()


@router.get("/v1/whoami", response_model=WhoAmIResponse)
async def whoami(email: str = Depends(authenticate)) -> WhoAmIResponse:
    row = await upsert_developer(email)
    return WhoAmIResponse(
        email=row["email"],
        display_name=row.get("display_name"),
        first_seen_at=row["first_seen_at"].isoformat(),
        last_seen_at=row["last_seen_at"].isoformat(),
    )
