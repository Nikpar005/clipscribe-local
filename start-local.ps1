$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"

if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    throw "FFmpeg is required but was not found. Install FFmpeg, add it to PATH, then run this file again."
}
if (-not (Get-Command node -ErrorAction SilentlyContinue) -or -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Node.js 24 is required for the web screen. Install Node.js, then run this file again."
}

if (-not (Test-Path -LiteralPath $python)) {
    $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        & py -3.14 -m venv (Join-Path $root ".venv")
        if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment. Install Python 3.14 and try again." }
    } else {
        & python -m venv (Join-Path $root ".venv")
        if ($LASTEXITCODE -ne 0) { throw "Could not create the Python environment. Install Python 3.14 and try again." }
    }
}

& $python -c "import clipscribe, fastapi, sqlalchemy, uvicorn"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing the app's Python packages (this may take a few minutes)..."
    & $python -m pip install -e .
    if ($LASTEXITCODE -ne 0) { throw "Python package installation failed. Check your internet connection and try again." }
}

$frontend = Join-Path $root "frontend"
if (-not (Test-Path -LiteralPath (Join-Path $frontend "node_modules"))) {
    Write-Host "Preparing the web screen..."
    Push-Location $frontend
    try { & npm ci; if ($LASTEXITCODE -ne 0) { throw "Web package installation failed." } }
    finally { Pop-Location }
}

New-Item -ItemType Directory -Path (Join-Path $root "data\local") -Force | Out-Null
Start-Process -FilePath $python -ArgumentList @("-m", "uvicorn", "clipscribe.main:app", "--host", "127.0.0.1", "--port", "8000") -WorkingDirectory $root
Start-Process -FilePath $env:ComSpec -ArgumentList @("/k", "npm run dev") -WorkingDirectory $frontend
Start-Sleep -Seconds 2
Start-Process "http://localhost:5173"
Write-Host "ClipScribe is opening at http://localhost:5173. Close the two opened terminal windows to stop it."
