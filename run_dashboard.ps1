param(
  [string]$HostAddress = "127.0.0.1",
  [int]$Port = 5000
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectRoot

$VenvDir = Join-Path $ProjectRoot ".venv"
$PythonExe = "python"

if (-not (Test-Path $VenvDir)) {
  & $PythonExe -m venv $VenvDir
}

$ActivateScript = Join-Path $VenvDir "Scripts\Activate.ps1"
if (-not (Test-Path $ActivateScript)) {
  throw "Virtualenv activation script not found at: $ActivateScript"
}

. $ActivateScript

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if (-not (Test-Path (Join-Path $ProjectRoot ".env"))) {
  Write-Host "Missing .env file in project root. Create one with: TEAM_NUMBER, DEFAULT_YEAR, BASE_URL, API_KEY" -ForegroundColor Yellow
  Write-Host "Example:" -ForegroundColor Yellow
  Write-Host "TEAM_NUMBER=1234" -ForegroundColor Yellow
  Write-Host "DEFAULT_YEAR=2026" -ForegroundColor Yellow
  Write-Host "BASE_URL=https://www.thebluealliance.com/api/v3" -ForegroundColor Yellow
  Write-Host "API_KEY=YOUR_TBA_KEY" -ForegroundColor Yellow
  throw "Cannot start app without required environment variables."
}

$env:FLASK_APP = "app.py"
$env:FLASK_ENV = "development"
$env:FLASK_RUN_HOST = $HostAddress
$env:FLASK_RUN_PORT = "$Port"

$Url = "http://$HostAddress`:$Port/"

Start-Process $Url

flask run
