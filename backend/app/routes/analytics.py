from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.services.analytics_service import get_analytics


router = APIRouter()


@router.get("/api/analytics", tags=["Analytics"])
def analytics_endpoint(db: Session = Depends(get_db)):
    return get_analytics(db)