"""Download the MOSS-Image model files into a ComfyUI models folder, resuming and verifying.

Each file is fetched with HTTP Range requests so an interrupted download (flaky Wi-Fi,
a security agent killing the process, a closed laptop) picks up where it stopped.
Every finished file is checked against the SHA-256 that Hugging Face publishes.

    python download_models.py C:\\ComfyUI\\models
"""
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request

REPO = "Comfy-Org/MOSS-Image"
FILES = [
    "vae/flux2-vae_small.safetensors",
    "diffusion_models/moss_image_sft_int8_convrot.safetensors",
    "text_encoders/qwen3.5_9b_w4a8_gptq.safetensors",
]


def expected():
    url = f"https://huggingface.co/api/models/{REPO}/tree/main?recursive=true"
    tree = json.load(urllib.request.urlopen(url, timeout=60))
    return {t["path"]: (t["size"], t.get("lfs", {}).get("oid")) for t in tree if t["type"] == "file"}


def fetch(url, dest, size):
    while True:
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        if have >= size:
            return
        req = urllib.request.Request(url, headers={"Range": f"bytes={have}-", "User-Agent": "QlikImagesComfyUI"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "ab" if r.status == 206 else "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
        except (urllib.error.URLError, OSError) as e:
            print(f"  retry at {have / 1e9:.2f} GB: {e}", flush=True)
            time.sleep(3)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def main(models_dir):
    want = expected()
    bad = 0
    for rel in FILES:
        size, oid = want[rel]
        dest = os.path.join(models_dir, *rel.split("/"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        print(f"{rel} ({size / 1e9:.2f} GB)", flush=True)
        fetch(f"https://huggingface.co/{REPO}/resolve/main/{rel}", dest, size)
        ok = sha256(dest) == oid
        print(f"  {'verified' if ok else 'CHECKSUM MISMATCH - delete the file and rerun'}", flush=True)
        bad += not ok
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join("ComfyUI", "models"))
