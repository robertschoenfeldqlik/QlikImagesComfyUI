# Installs ComfyUI with MOSS-Image and the Qlik technical architecture workflows (Windows, NVIDIA GPU).
#   powershell -ExecutionPolicy Bypass -File scripts\install.ps1 -ComfyRoot C:\ComfyUI
param(
    [string]$ComfyRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) 'ComfyUI'),
    [string]$Python = 'python',
    [string]$TorchIndex = 'https://download.pytorch.org/whl/cu130'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent

if (-not (Test-Path (Join-Path $ComfyRoot 'main.py'))) {
    git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git $ComfyRoot
    if ($LASTEXITCODE) { throw 'git clone failed' }
}
$venvPy = Join-Path $ComfyRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPy)) { & $Python -m venv (Join-Path $ComfyRoot '.venv') }

& $venvPy -m pip install --upgrade pip
# --index-url, not --extra-index-url: with an extra index pip can pick the CPU-only wheel from PyPI.
& $venvPy -m pip install torch torchvision torchaudio --index-url $TorchIndex
if ($LASTEXITCODE) { throw 'PyTorch install failed' }
& $venvPy -m pip install -r (Join-Path $ComfyRoot 'requirements.txt')
if ($LASTEXITCODE) { throw 'ComfyUI requirements install failed' }
& $venvPy -c "import torch,sys; ok=torch.cuda.is_available(); print('torch', torch.__version__, 'CUDA', torch.version.cuda, 'GPU', torch.cuda.get_device_name(0) if ok else 'NONE'); sys.exit(0 if ok else 1)"
if ($LASTEXITCODE) { throw 'PyTorch cannot see the GPU' }

# Downloads resume after interruptions; rerun until every file reports "verified".
do {
    & $venvPy (Join-Path $repo 'scripts\download_models.py') (Join-Path $ComfyRoot 'models')
} while ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1)
if ($LASTEXITCODE) { throw 'Model checksum mismatch' }

# Install the workflows as a custom node so they open from a URL (?template=...&source=qlik-tech-arch)
$node = Join-Path $ComfyRoot 'custom_nodes\qlik-tech-arch'
New-Item -ItemType Directory -Force (Join-Path $node 'example_workflows') | Out-Null
Copy-Item (Join-Path $repo 'custom_node\__init__.py') $node -Force
Copy-Item (Join-Path $repo 'custom_node\example_workflows\*.json') (Join-Path $node 'example_workflows') -Force
# ...and into the Workflows panel
$wf = Join-Path $ComfyRoot 'user\default\workflows'
New-Item -ItemType Directory -Force $wf | Out-Null
Copy-Item (Join-Path $repo 'custom_node\example_workflows\*.json') $wf -Force
# Official Qlik logo the workflows composite onto each render
Copy-Item (Join-Path $repo 'assets\qlik-logo-header*.png') (Join-Path $ComfyRoot 'input') -Force
Write-Host "Installed. Start with: scripts\run.ps1 -ComfyRoot $ComfyRoot"
