import asyncio
import base64
import json
import os
import re

from PIL import Image

from services.tryon.segmentation.body import UnifiedBodySegmenter
from services.tryon.vision.pose import PoseDetector


def _decode_data_uri(data_uri: str) -> bytes:
    m = re.match(r"^data:([^;]+);base64,(.*)$", data_uri)
    if not m:
        return base64.b64decode(data_uri)
    return base64.b64decode(m.group(2))


def main() -> None:
    req_path = os.path.join(os.path.dirname(__file__), "tmp_tryon_request.json")
    with open(req_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    user_b64 = data["userImageBase64"]
    img_bytes = _decode_data_uri(user_b64)
    img = Image.open(__import__("io").BytesIO(img_bytes)).convert("RGB")

    pose_detector = PoseDetector()
    seg = UnifiedBodySegmenter()

    async def _run():
        pose = await pose_detector.detect_from_pil(img)
        return pose

    pose = asyncio.run(_run())
    print("pose.success:", pose.success, "confidence:", pose.confidence, "landmarks:", len(pose.landmarks))

    pack = seg.build(img_bytes, pose)
    print("seg.source:", pack.segmentation_source, "conf:", pack.segmentation_confidence)

    out_dir = os.path.dirname(__file__)
    pack.torso_mask.astype("uint8").tofile(os.path.join(out_dir, "___torso_mask_u8.bin"))

    # Save masks as PNGs for quick visual check.
    import cv2
    cv2.imwrite(os.path.join(out_dir, "local_dbg_person_mask.png"), pack.person_mask.astype("uint8"))
    cv2.imwrite(os.path.join(out_dir, "local_dbg_torso_mask.png"), pack.torso_mask.astype("uint8"))
    cv2.imwrite(
        os.path.join(out_dir, "local_dbg_arms_mask.png"), pack.arms_mask.astype("uint8")
    )
    if pack.garment_clip_mask is not None:
        cv2.imwrite(
            os.path.join(out_dir, "local_dbg_garment_clip_mask.png"),
            pack.garment_clip_mask.astype("uint8"),
        )


if __name__ == "__main__":
    main()

