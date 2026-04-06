from typing import List
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database.session import get_db
from database.models import DigitalTwin
from models.digital_twin_models import (
    DigitalTwinCreateRequest,
    DigitalTwinProfileResponse,
    DigitalTwinRenderRequest,
    DigitalTwinRenderResponse,
)
from utils.auth_deps import require_auth
from services.auth_service import UserProfile

router = APIRouter(prefix="/api/digital-twin", tags=["digital-twin"])


@router.post("", response_model=DigitalTwinProfileResponse)
async def create_digital_twin(
    payload: DigitalTwinCreateRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """
    Start a new digital twin training session for the current user.

    This endpoint stores metadata and marks the twin as `pending`. A separate
    GPU-powered microservice (not implemented here) can pick up the row and
    perform actual model training, then update `status` and `twin_image_url`.
    """
    now = datetime.utcnow()

    row = DigitalTwin(
        user_id=user.id,
        reference_images=payload.photo_urls,
        status="pending",
        meta={},
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return DigitalTwinProfileResponse.model_validate(row)


@router.get("", response_model=List[DigitalTwinProfileResponse])
async def list_digital_twins(
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    rows = (
        db.query(DigitalTwin)
        .filter(DigitalTwin.user_id == user.id)
        .order_by(DigitalTwin.created_at.desc())
        .all()
    )
    return [DigitalTwinProfileResponse.model_validate(r) for r in rows]


@router.post("/{twin_id}/renders", response_model=DigitalTwinRenderResponse)
async def create_twin_render(
    twin_id: str,
    payload: DigitalTwinRenderRequest,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    """
    Request a new render for a digital twin.

    For now this simulates the final image using a placeholder URL. In a
    production setup, this would call an external Stable Diffusion / IDM-VTON
    microservice and store the returned image URL.
    """
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid twin ID format")

    twin = (
        db.query(DigitalTwin)
        .filter(
            DigitalTwin.id == twin_uuid,
            DigitalTwin.user_id == user.id,
        )
        .first()
    )
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")

    # Placeholder demo image; replace with real VTON output URL later.
    placeholder_url = "https://images.unsplash.com/photo-1487412720507-e7ab37603c6f?w=800&q=80"

    # For now, update the twin with the render URL
    twin.twin_image_url = placeholder_url
    twin.environment = payload.environment
    twin.meta = {"garment_product_id": payload.garment_product_id}
    twin.status = "complete"
    twin.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(twin)

    # Return a render response (simulated)
    return DigitalTwinRenderResponse(
        id=str(uuid.uuid4()),
        twin_id=str(twin.id),
        environment=payload.environment,
        garment_product_id=payload.garment_product_id,
        image_url=placeholder_url,
        created_at=datetime.utcnow(),
    )


@router.get("/{twin_id}/renders", response_model=List[DigitalTwinRenderResponse])
async def list_twin_renders(
    twin_id: str,
    db: Session = Depends(get_db),
    user: UserProfile = Depends(require_auth),
):
    try:
        twin_uuid = uuid.UUID(twin_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid twin ID format")

    twin = (
        db.query(DigitalTwin)
        .filter(
            DigitalTwin.id == twin_uuid,
            DigitalTwin.user_id == user.id,
        )
        .first()
    )
    if not twin:
        raise HTTPException(status_code=404, detail="Digital twin not found")

    # Since we don't have a separate render table, return a single render if image exists
    if twin.twin_image_url:
        return [
            DigitalTwinRenderResponse(
                id=str(uuid.uuid4()),
                twin_id=str(twin.id),
                environment=twin.environment,
                garment_product_id=twin.meta.get("garment_product_id"),
                image_url=twin.twin_image_url,
                created_at=twin.updated_at,
            )
        ]
    return []

