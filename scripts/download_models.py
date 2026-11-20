"""Download the MOSS-Image model files into a ComfyUI models folder, resuming and verifying.

Each file is fetched with HTTP Range requests so an interrupted download (flaky Wi-Fi,
a security agent killing the process, a closed laptop) picks up where it stopped.
Every finished file is checked against its pinned SHA-256.

Hashing never happens in a process that has used the network: some endpoint security agents
kill a process that downloads and then reads a multi-GB file. A run that downloaded anything
exits with NEEDS_VERIFY; run it again and the second run, with nothing left to fetch, verifies
offline. install.ps1 does this automatically.

    python download_models.py C:\\ComfyUI\\models
"""
import hashlib
import os
import sys
import time
import urllib.error
import urllib.request

REPO = "Comfy-Org/MOSS-Image"
REVISION = "2929efe3cdd506c0a430bcfca70a9a8d805cc095"     # pinned so sizes and hashes below stay valid
FILES = [   # (path in the repo and under models/, size in bytes, SHA-256 published by Hugging Face)
    ("vae/flux2-vae_small.safetensors", 249521340,
     "d8d52ba036475f5fb07c8b435e176d3d97ebfa82f0d1a1c317f9cc1e25bd013b"),
    ("diffusion_models/moss_image_sft_int8_convrot.safetensors", 5413698958,
     "b4d1475bc7eeffd7b809e82ea13a1fba1fb85c4e18365af3813722faa5c0fe4f"),
    ("text_encoders/qwen3.5_9b_w4a8_gptq.safetensors", 7343591088,
     "4cc6a1543ad2061806da46f35f90cadb4801dcba246c44782cf42ec0feb6407c"),
    ("loras/moss_image_edit_lora_rank_64_bf16.safetensors", 297382216,    # img-photo-to-cartoon and -bowtie
     "17a48b8c605dcffdedb92a2b887d18cf316505be90802717669fb6556098dcdf"),
]
CHECKSUM_FAILED = 3   # install.ps1 stops on this code
NEEDS_VERIFY = 4      # downloaded this run; rerun to verify offline
MAX_ATTEMPTS = 20     # consecutive failures with no progress before giving up


def permanent(e):
    """A 4xx other than timeout or rate limit will not fix itself by retrying (missing file, gated repo)."""
    return isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500 and e.code not in (408, 429)


def fetch(url, dest, size):
    failures = 0     # reset whenever the file grows
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
            if permanent(e):
                raise
            failures = 0 if os.path.exists(dest) and os.path.getsize(dest) > have else failures + 1
            if failures >= MAX_ATTEMPTS:
                raise
            print(f"  retry at {have / 1e9:.2f} GB: {e}", flush=True)
            time.sleep(3)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while b := f.read(1 << 24):
            h.update(b)
    return h.hexdigest()


def main(models_dir):
    downloaded = False
    for rel, size, _ in FILES:
        dest = os.path.join(models_dir, *rel.split("/"))
        have = os.path.getsize(dest) if os.path.exists(dest) else 0
        if have < size:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            print(f"{rel} ({size / 1e9:.2f} GB) downloading from {have / 1e9:.2f} GB", flush=True)
            fetch(f"https://huggingface.co/{REPO}/resolve/{REVISION}/{rel}", dest, size)
            downloaded = True
    if downloaded:
        print("Downloads complete. Run again to verify checksums.", flush=True)
        sys.exit(NEEDS_VERIFY)
    bad = 0
    for rel, size, oid in FILES:
        dest = os.path.join(models_dir, *rel.split("/"))
        ok = os.path.getsize(dest) == size and sha256(dest) == oid
        print(f"{rel} ({size / 1e9:.2f} GB)\n  {'verified' if ok else 'CHECKSUM MISMATCH - delete the file and rerun'}",
              flush=True)
        bad += not ok
    sys.exit(CHECKSUM_FAILED if bad else 0)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join("ComfyUI", "models"))
