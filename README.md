# QlikImagesComfyUI

Qlik-branded technical architecture diagrams and marketing assets generated locally with [ComfyUI](https://github.com/comfyanonymous/ComfyUI) and [MOSS-Image](https://github.com/OpenMOSS/MOSS-Image), a 5B open-weights (Apache 2.0) text-to-image model that renders text and follows box layouts. All content is generic and editable.

Each workflow goes further than a plain prompt to a frontier image model:

1. **Layout control.** Every zone, card, arrow, label, button and illustration is a bounding box with its own caption and Qlik palette, so elements and text land exactly where they are placed.
2. **Refine pass.** The 1 MP render is upscaled 1.5× in pixel space, re-encoded and re-sampled at 0.45 denoise, for a sharper result (2032×1152 for 16:9).
3. **Official logo.** The real Qlik logo is composited top-right after generation, never redrawn by the model.

## Workflows

| Workflow | Format | Content |
|---|---|---|
| `tech-arch-data-pipeline` | 16:9 | ERP, CRM and event streams → Qlik Talend Cloud → cloud data platform (landing, curated tables, catalog) → data warehouse and Qlik Cloud Analytics |
| `tech-arch-cloud-network` | 16:9 | Users → CDN / WAF → virtual network across two availability zones with load balancers, NAT, app services and managed databases |
| `tech-arch-microservices` | 16:9 | Clients → API gateway → Kubernetes services → Kafka → Qlik Talend Cloud → Qlik Sense, Qlik Answers, Qlik Automate |
| `tech-arch-layered-stack` | 16:9 | Platform layers from data movement to AI answers, with a trust and governance column |
| `mkt-webinar-promo` | 16:9 | Webinar promotion with label, headline, date line and Register button |
| `mkt-social-square` | 1:1 | Social post with headline, illustration and Learn More button |
| `mkt-web-banner` | 21:9 | Website or LinkedIn hero banner with headline and Get Started button |
| `mkt-product-hero` | 16:9 | Product launch hero with floating chart panels and call to action |
| `fun-comic-product-mgmt` | 21:9 | Three-panel office comic: the data-driven roadmap |
| `fun-comic-standup` | 21:9 | Three-panel office comic: the daily standup |
| `fun-comic-spreadsheet` | 21:9 | Three-panel office comic: the new dashboard |
| `fun-comic-ai-strategy` | 21:9 | Three-panel office comic: the AI strategy |
| `fun-poster-last-dashboard` | 2:3 | Spoof sci-fi movie poster |
| `fun-poster-deadline-friday` | 2:3 | Spoof thriller movie poster |
| `fun-poster-rogue-pipeline` | 2:3 | Spoof heist movie poster |
| `fun-poster-schema-drift` | 2:3 | Spoof horror movie poster |
| `fun-poster-legacy-system` | 2:3 | Spoof western movie poster |
| `fun-poster-latency` | 2:3 | Spoof romantic comedy poster |

The comics and posters are original: their own characters, jokes and titles, not based on any existing comic strip or film. Comics use a dark-text version of the official logo for their white page.

The style is the Qlik navy theme: a flat navy canvas, darker navy glass panels with cyan hairlines, Qlik green `#009845` cards for Qlik products and buttons, glowing green connectors and Inter typography.

## Requirements

- Windows with an NVIDIA GPU (tested on a 4 GB RTX A500 with `--lowvram`, about 10 minutes per image), Python 3.12 and git
- About 15 GB of disk for the models and Python environment

## Install

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install.ps1
```

ComfyUI installs into `ComfyUI\` inside this folder (ignored by git); pass `-ComfyRoot` to put it elsewhere. The script:
- clones ComfyUI and installs CUDA PyTorch and ComfyUI's requirements
- downloads the model files with resume and verifies each one's SHA-256
- installs the workflows as the `qlik-tech-arch` custom node
- copies the official logo into ComfyUI's `input` folder

| File | Size | Folder |
|---|---|---|
| `moss_image_sft_int8_convrot.safetensors` | 5.04 GB | `models/diffusion_models` |
| `qwen3.5_9b_w4a8_gptq.safetensors` | 6.84 GB | `models/text_encoders` |
| `flux2-vae_small.safetensors` | 0.23 GB | `models/vae` |

Weights come from [Comfy-Org/MOSS-Image](https://huggingface.co/Comfy-Org/MOSS-Image) and are not stored in this repository.

## Run

```powershell
powershell -ExecutionPolicy Bypass -File scripts\run.ps1
```

Open a workflow directly with `http://127.0.0.1:8188/?template=<workflow>&source=qlik-tech-arch`, for example:

- http://127.0.0.1:8188/?template=tech-arch-data-pipeline&source=qlik-tech-arch
- http://127.0.0.1:8188/?template=mkt-webinar-promo&source=qlik-tech-arch

Click **Run**. Output lands in `ComfyUI\output\` with the workflow name as the prefix.

## Edit

- **In the UI:** open `Create Bounding Boxes`, then move, resize or retype boxes (requires ComfyUI's Nodes 2.0 mode). Keep the background box first.
- **In code:** layouts live in `tools/build_tech_arch.py`. Diagrams use `zone`, `comp`, `arrow` and `edge_label`; marketing assets use `headline`, `subline`, `pill`, `button` and `hero_art`; comics use `comic_strip` (title, three scenes, who is in each, what they say); posters use `poster`. Labels beginning with "Qlik" become green Qlik cards. Regenerate with:

```powershell
python tools\build_tech_arch.py
```

Keep the prompt enhancer off in these workflows, because it rewrites the layout JSON and can drop the boxes. Keep text out of the top-right corner, where the logo goes; the builder rejects layouts that put text there.
