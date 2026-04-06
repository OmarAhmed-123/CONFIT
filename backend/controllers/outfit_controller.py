from typing import List, Optional

from fastapi import HTTPException

from models.outfit_models import OutfitCreate, OutfitUpdate, OutfitResponse
from services.outfit_service import OutfitService


class OutfitController:
    """Controller layer for the Outfit Builder feature."""

    def __init__(self, service: OutfitService) -> None:
        self._service = service

    async def create_outfit(self, user_id: str, payload: OutfitCreate) -> OutfitResponse:
        return self._service.create_outfit(user_id, payload)

    async def list_outfits(self, user_id: str) -> List[OutfitResponse]:
        return self._service.list_outfits(user_id)

    async def get_outfit(self, user_id: str, outfit_id: str) -> OutfitResponse:
        outfit = self._service.get_outfit(user_id, outfit_id)
        if not outfit:
            raise HTTPException(status_code=404, detail="Outfit not found")
        return outfit

    async def update_outfit(
        self,
        user_id: str,
        outfit_id: str,
        payload: OutfitUpdate,
    ) -> OutfitResponse:
        outfit = self._service.update_outfit(user_id, outfit_id, payload)
        if not outfit:
            raise HTTPException(status_code=404, detail="Outfit not found")
        return outfit

    async def delete_outfit(self, user_id: str, outfit_id: str) -> None:
        if not self._service.delete_outfit(user_id, outfit_id):
            raise HTTPException(status_code=404, detail="Outfit not found")

    async def get_shared_outfit(self, share_slug: str) -> OutfitResponse:
        outfit = self._service.get_outfit_by_slug(share_slug)
        if not outfit:
            raise HTTPException(status_code=404, detail="Shared outfit not found")
        return outfit

