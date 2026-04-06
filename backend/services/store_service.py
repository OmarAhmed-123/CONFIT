"""
CONFIT Backend — Store Service
===============================
Store CRUD backed by the database. Use via Depends(get_db).
"""

import uuid
from typing import List, Optional

from sqlalchemy.orm import Session

from database.models import Store as StoreModel
from models.store_models import StoreResponse, StoreCreate, GeoLocation


def _row_to_response(row: StoreModel) -> StoreResponse:
    """Map ORM row to API response."""
    loc = None
    if row.location and isinstance(row.location, dict):
        loc = GeoLocation(lat=row.location.get("lat", 0), lng=row.location.get("lng", 0))
    return StoreResponse(
        id=row.id,
        name=row.name,
        brand_id=row.brand_id,
        address=row.address,
        city=row.city,
        state=row.state,
        country=row.country,
        postal_code=row.postal_code,
        phone=row.phone,
        email=row.email,
        location=loc,
        hours=row.hours or {},
        services=row.services or [],
    )


class StoreService:
    """Store management with database persistence."""

    def __init__(self, db: Session):
        self._db = db

    async def get_stores(self, brand_id: Optional[str] = None) -> List[StoreResponse]:
        q = self._db.query(StoreModel).order_by(StoreModel.name)
        if brand_id:
            q = q.filter(StoreModel.brand_id == brand_id)
        rows = q.all()
        return [_row_to_response(r) for r in rows]

    async def create_store(self, store: StoreCreate) -> StoreResponse:
        s_id = f"store-{uuid.uuid4().hex[:8]}"
        loc = store.location.model_dump() if store.location else None
        hours = store.hours if isinstance(store.hours, dict) else {}
        services = list(store.services) if store.services else []

        row = StoreModel(
            id=s_id,
            brand_id=store.brand_id,
            name=store.name,
            address=store.address,
            city=store.city,
            state=store.state,
            country=store.country,
            postal_code=store.postal_code,
            phone=store.phone,
            email=store.email,
            location=loc,
            hours=hours,
            services=services,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _row_to_response(row)

    def get_stores_with_bopis(self) -> List[StoreModel]:
        """Return store rows that offer BOPIS (for availability checks)."""
        rows = self._db.query(StoreModel).all()
        return [r for r in rows if r.services and "BOPIS" in r.services]
