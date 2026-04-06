import base64
import json
import os
import re
import urllib.parse

import requests
from PIL import Image

import cv2

from services.tryon.warping.garment import GarmentProcessor


def _load_tmp_request() -> dict:
    req_path = os.path.join(os.path.dirname(__file__), "tmp_tryon_request.json")
    with open(req_path, "r", encoding="utf-8") as f:
        return json.load(f)


def main() -> None:
    data = _load_tmp_request()
    garment_url = data["garmentImageUrl"]
    garment_name = data.get("garmentName", "garment")

    print("garment_url:", garment_url)
    print("garment_name:", garment_name)

    r = requests.get(garment_url, timeout=120)
    r.raise_for_status()

    img = Image.open(io.BytesIO(r.content)).convert("RGB")  # type: ignore[name-defined]

    gp = GarmentProcessor()
    processed, alpha_u8 = gp._remove_background_sync(img)  # type: ignore[attr-defined]

    out_dir = os.path.dirname(__file__)
    processed_path = os.path.join(out_dir, "local_dbg_garment_processed.png")
    alpha_path = os.path.join(out_dir, "local_dbg_garment_alpha_u8.png")
    cv2.imwrite(alpha_path, alpha_u8)
    processed.save(processed_path)
    print("saved:", processed_path)
    print("saved:", alpha_path)


if __name__ == "__main__":
    import io

    main()

