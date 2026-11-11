# Starts ComfyUI on http://127.0.0.1:8188. --lowvram keeps the 5 GB model and 7 GB text encoder
# usable on small GPUs by streaming weights from system RAM; drop it on GPUs with 16 GB or more.
param(
    [string]$ComfyRoot = (Join-Path (Split-Path $PSScriptRoot -Parent) 'ComfyUI'),
    [int]$Port = 8188,
    [switch]$HighVram
)
$cliArgs = @((Join-Path $ComfyRoot 'main.py'), '--listen', '127.0.0.1', '--port', $Port)
if (-not $HighVram) { $cliArgs += '--lowvram' }
& (Join-Path $ComfyRoot '.venv\Scripts\python.exe') @cliArgs
