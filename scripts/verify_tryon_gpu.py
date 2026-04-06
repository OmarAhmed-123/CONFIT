import os
import requests
import torch


def main() -> None:
    print("cuda_available:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("gpu_name:", torch.cuda.get_device_name(0))
        props = torch.cuda.get_device_properties(0)
        print("vram_gb:", round(props.total_memory / (1024**3), 2))
    else:
        print("gpu_name: NO GPU")

    base = os.getenv("TRYON_BACKEND_URL", "http://127.0.0.1:8000")
    for path in ("/api/health", "/api/virtual-tryon/diagnostics"):
        url = f"{base}{path}"
        try:
            r = requests.get(url, timeout=8)
            print(path, "->", r.status_code)
            print(r.text[:500])
        except Exception as exc:
            print(path, "-> ERROR:", exc)


if __name__ == "__main__":
    main()

