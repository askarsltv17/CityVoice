$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Get-PythonLauncher {
  if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
      & py -3.13 --version *> $null
      if ($LASTEXITCODE -eq 0) {
        return @("py", "-3.13")
      }
    } catch {
    }

    try {
      & py --version *> $null
      if ($LASTEXITCODE -eq 0) {
        return @("py")
      }
    } catch {
    }
  }

  if (Get-Command python -ErrorAction SilentlyContinue) {
    try {
      & python --version *> $null
      if ($LASTEXITCODE -eq 0) {
        return @("python")
      }
    } catch {
    }
  }

  throw "Python 3.13 is not installed or not available in PATH. Install Python and enable 'Add python.exe to PATH'."
}

function Invoke-PythonLauncher {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)

  & $script:PythonLauncherCommand @script:PythonLauncherArgs @Arguments
}

function Test-VenvHealth {
  param(
    [string]$PythonPath,
    [string]$ConfigPath
  )

  if (-not (Test-Path $PythonPath) -or -not (Test-Path $ConfigPath)) {
    return $false
  }

  try {
    $config = Get-Content $ConfigPath -Raw
    $executableLine = ($config -split "\r?\n" | Where-Object { $_ -like "executable = *" } | Select-Object -First 1)

    if ($executableLine) {
      $basePython = $executableLine.Substring("executable = ".Length).Trim()
      if ($basePython -and -not (Test-Path $basePython)) {
        return $false
      }
    }

    & $PythonPath --version *> $null
    return $LASTEXITCODE -eq 0
  } catch {
    return $false
  }
}

$pythonLauncher = Get-PythonLauncher
$script:PythonLauncherCommand = $pythonLauncher[0]
$script:PythonLauncherArgs = @()
if ($pythonLauncher.Count -gt 1) {
  $script:PythonLauncherArgs = $pythonLauncher[1..($pythonLauncher.Count - 1)]
}

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
$venvConfig = Join-Path $PSScriptRoot ".venv\pyvenv.cfg"

Write-Host "Starting CityVoice with PostgreSQL from .env settings."
Write-Host "Make sure your PostgreSQL server is already running before launch."

if (-not (Test-VenvHealth -PythonPath $venvPython -ConfigPath $venvConfig)) {
  if (Test-Path (Join-Path $PSScriptRoot ".venv")) {
    Write-Host "Detected a broken or чужой .venv. Recreating it for this PC..."
    Remove-Item -LiteralPath (Join-Path $PSScriptRoot ".venv") -Recurse -Force
  } else {
    Write-Host "Creating .venv..."
  }

  Invoke-PythonLauncher -m venv .venv
}

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r requirements.txt
& $venvPython app.py
