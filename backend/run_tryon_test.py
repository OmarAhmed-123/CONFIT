import base64
import json
import os
import re
import sys
from typing import Any, Dict

import requests


def _decode_data_uri(data_uri: str) -> tuple[bytes, str]:
    """
    Decode a `data:*;base64,...` URI into (bytes, file_ext).
    """
    m = re.match(r"^data:([^;]+);base64,(.*)$", data_uri)
    if not m:
        # Assume raw base64
        return base64.b64decode(data_uri), "png"

    mime = m.group(1)
    b64 = m.group(2)
    if "png" in mime:
        ext = "png"
    elif "jpeg" in mime or "jpg" in mime:
        ext = "jpg"
    else:
        ext = "png"
    return base64.b64decode(b64), ext


def main() -> None:
    req_path = os.path.join(os.path.dirname(__file__), "tmp_tryon_request.json")
    url = os.getenv("TRYON_TEST_URL", "http://127.0.0.1:8001/api/virtual-tryon/process")
    qt = float(os.getenv("TRYON_TEST_QUALITY_THRESHOLD", "0.58"))

    with open(req_path, "r", encoding="utf-8") as f:
        payload: Dict[str, Any] = json.load(f)

    # Options: change qualityThreshold to bust cache + force validation path.
    options = {
        "fitType": "regular",
        "qualityThreshold": qt,
        "enableValidation": True,
        "returnValidationDetails": False,
        "fabricPhysicsEnabled": os.getenv("TRYON_TEST_FABRIC_PHYSICS", "1").strip().lower() in (
            "1",
            "true",
            "yes",
        ),
        "fabricLowPower": False,
        "skipPoseDetection": False,
        "noPersistBodyDna": False,
        "useStoredBodyDna": False,
        "learnBodyDna": False,
        "forceRefreshBodyDna": False,
        "allowLowQualityOutput": False,
    }
    payload["options"] = options

    # Help category hint (optional, but safe).
    payload.setdefault("garmentCategory", "tops")

    resp = requests.post(url, json=payload, timeout=300)
    print("HTTP", resp.status_code)
    j = resp.json()
    print("success:", j.get("success"))
    print("qualityScore:", j.get("qualityScore"))
    print("poseDetected:", j.get("poseDetected"))
    print("cacheHit:", j.get("cacheHit"))
    print("warnings:", j.get("warnings"))
    print("message:", j.get("message"))

    img = j.get("resultImage")
    if not img:
        print("No resultImage in response (full payload):", file=sys.stderr)
        try:
            print(json.dumps(j, ensure_ascii=False, indent=2), file=sys.stderr)
        except Exception:
            print(str(j), file=sys.stderr)
        sys.exit(2)

    raw_bytes, ext = _decode_data_uri(img)
    out_path = os.path.join(
        os.path.dirname(__file__),
        f"tryon_debug_after_torso_clip_q{str(qt).replace('.', 'p')}.{ext}",
    )
    with open(out_path, "wb") as f:
        f.write(raw_bytes)
    print("saved:", out_path)


if __name__ == "__main__":
    main()

