"""
CONFIT Backend - Cart Compatibility Router
==========================================
Small authenticated cart API used by shared frontend hooks. The main shopper
cart remains client-side, but these endpoints keep API consumers on stable JSON.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends

from services.auth_service import UserProfile
from utils.auth_deps import optional_auth

router = APIRouter(prefix="/api/cart", tags=["Cart"])

_CARTS: dict[str, list[dict[str, Any]]] = {}


def _cart_key(user: UserProfile | None) -> str:
    return user.id if user else "guest"


def _quantity(value: Any) -> int:
    try:
        return max(1, int(value or 1))
    except (TypeError, ValueError):
        return 1


@router.get("")
async def get_cart(user: UserProfile | None = Depends(optional_auth)) -> dict[str, Any]:
    items = _CARTS.get(_cart_key(user), [])
    return {"success": True, "items": items, "total_items": len(items)}


@router.post("/items")
async def add_cart_item(
    payload: dict[str, Any] = Body(default_factory=dict),
    user: UserProfile | None = Depends(optional_auth),
) -> dict[str, Any]:
    key = _cart_key(user)
    item = {
        "id": str(payload.get("id") or payload.get("productId") or payload.get("product_id") or len(_CARTS.get(key, [])) + 1),
        "productId": payload.get("productId") or payload.get("product_id"),
        "size": payload.get("size") or "One Size",
        "color": payload.get("color") or "Default",
        "quantity": _quantity(payload.get("quantity")),
    }
    _CARTS.setdefault(key, []).append(item)
    return {"success": True, "item": item, "items": _CARTS[key]}


@router.patch("/items/{item_id}")
async def update_cart_item(
    item_id: str,
    payload: dict[str, Any] = Body(default_factory=dict),
    user: UserProfile | None = Depends(optional_auth),
) -> dict[str, Any]:
    key = _cart_key(user)
    items = _CARTS.setdefault(key, [])
    for item in items:
        if str(item.get("id")) == item_id:
            item.update({k: v for k, v in payload.items() if k in {"size", "color", "quantity"}})
            if "quantity" in item:
                item["quantity"] = _quantity(item["quantity"])
            return {"success": True, "item": item, "items": items}
    return {"success": True, "item": None, "items": items}


@router.delete("/items/{item_id}")
async def remove_cart_item(
    item_id: str,
    user: UserProfile | None = Depends(optional_auth),
) -> dict[str, Any]:
    key = _cart_key(user)
    _CARTS[key] = [item for item in _CARTS.get(key, []) if str(item.get("id")) != item_id]
    return {"success": True, "items": _CARTS[key]}


@router.post("/clear")
async def clear_cart(user: UserProfile | None = Depends(optional_auth)) -> dict[str, Any]:
    _CARTS[_cart_key(user)] = []
    return {"success": True, "items": []}
