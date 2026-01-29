	param(
	    [string]$AppDir = (Resolve-Path $PSScriptRoot).Path,
	    [string]$VenvDir = "",
	    [string]$Requirements = "",
	    [string]$LogFile = "",
	    [string]$PythonVersion = "3.10.11",
	    [ValidateSet("amd64")][string]$PythonArch = "amd64",
	    [switch]$InstallAllUsers,
	    [switch]$SkipHealthCheck,
	    [switch]$SkipMT5Wizard,
	    [switch]$AllowUnpinned
	)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

if ([string]::IsNullOrWhiteSpace($VenvDir)) {
    $VenvDir = Join-Path $AppDir "venv"
}
if ([string]::IsNullOrWhiteSpace($Requirements)) {
    $Requirements = Join-Path $AppDir "requirements.txt"
}
	if ([string]::IsNullOrWhiteSpace($LogFile)) {
	    $LogFile = Join-Path $AppDir "logs\setup.log"
	}

	$MT5DownloadUrl = "https://www.metatrader5.com/pt/download"

	function Write-Log {
	    param([string]$Message)
	    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
	    $line = "$timestamp - $Message"
	    Write-Output $line
    $logDir = Split-Path -Parent $LogFile
    if (-not (Test-Path $logDir)) {
        New-Item -ItemType Directory -Path $logDir -Force | Out-Null
    }
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

function Fail {
    param([string]$Message)
    Write-Log "ERROR: $Message"
    throw $Message
}

function Assert-RequirementsPinned {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Fail "requirements.txt not found at $Path"
    }
    $lines = Get-Content -Path $Path
    foreach ($line in $lines) {
        $trim = $line.Trim()
        if ($trim -eq "" -or $trim.StartsWith("#")) {
            continue
        }
        if ($trim.StartsWith("-")) {
            continue
        }
        if ($trim -match "==|===|@") {
            continue
        }
        Fail "Unpinned requirement detected: $trim (use -AllowUnpinned to ignore)"
    }
}

function Is-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
}

function Get-TargetMajorMinor {
    param([string]$Version)
    $parts = $Version.Split(".")
    if ($parts.Length -lt 2) {
        Fail "Invalid PythonVersion: $Version"
    }
    return "$($parts[0]).$($parts[1])"
}

function Find-Python {
    param([string]$TargetVersion)
    $targetMajorMinor = Get-TargetMajorMinor -Version $TargetVersion
    $py = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($py) {
        try {
            $output = & py -$targetMajorMinor -c "import sys; print(sys.executable); print('%d.%d.%d' % sys.version_info[:3])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $output.Count -ge 2) {
                return @{
                    Path = $output[0].Trim()
                    Version = $output[1].Trim()
                }
            }
        } catch {
        }
    }

    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    if ($python) {
        try {
            $output = & python -c "import sys; print(sys.executable); print('%d.%d.%d' % sys.version_info[:3])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $output.Count -ge 2) {
                return @{
                    Path = $output[0].Trim()
                    Version = $output[1].Trim()
                }
            }
        } catch {
        }
    }
    return $null
}

	function Resolve-InstalledPython {
	    param(
	        [string]$PreferredPath,
	        [string]$TargetVersion,
	        [switch]$AllUsers
	    )

    if ($PreferredPath -and (Test-Path $PreferredPath)) {
        return $PreferredPath
    }

    $roots = @()
    if ($env:LOCALAPPDATA) { $roots += (Join-Path $env:LOCALAPPDATA "Programs\Python") }
    if ($env:ProgramFiles) { $roots += $env:ProgramFiles }
    if ($env:ProgramFiles -and (Test-Path "${env:ProgramFiles(x86)}")) { $roots += ${env:ProgramFiles(x86)} }
    $roots = $roots | Select-Object -Unique

    $candidates = @()
    foreach ($root in $roots) {
        if (-not (Test-Path $root)) { continue }
        Get-ChildItem -Path $root -Directory -Filter "Python*" -ErrorAction SilentlyContinue | ForEach-Object {
            $exe = Join-Path $_.FullName "python.exe"
            if (Test-Path $exe) {
                $candidates += $exe
            }
        }
    }

    $targetMajorMinor = Get-TargetMajorMinor -Version $TargetVersion
    $targetVersionObj = [version]$TargetVersion
    $best = $null
    $bestVersion = [version]"0.0.0"

    foreach ($exe in $candidates | Select-Object -Unique) {
        try {
            $output = & $exe -c "import sys; print('%d.%d.%d' % sys.version_info[:3])" 2>$null
            if ($LASTEXITCODE -ne 0 -or -not $output) { continue }
            $ver = [version]$output.Trim()
            $majorMinor = Get-TargetMajorMinor -Version $output.Trim()
            if ($majorMinor -eq $targetMajorMinor -and $ver -ge $targetVersionObj) {
                if ($ver -gt $bestVersion) {
                    $bestVersion = $ver
                    $best = $exe
                }
            }
        } catch {
        }
    }

	    return $best
	}

	function Get-ConfiguredMT5Terminal {
	    param([string]$ConfigPath)
	    if (-not (Test-Path -LiteralPath $ConfigPath)) {
	        return $null
	    }
	    try {
	        $cfg = Get-Content -Raw -Path $ConfigPath -ErrorAction Stop | ConvertFrom-Json
	    } catch {
	        return $null
	    }
	    $path = $cfg.terminal_path
	    if ([string]::IsNullOrWhiteSpace($path)) {
	        return $null
	    }
	    try {
	        if (Test-Path -LiteralPath $path) {
	            return $path
	        }
	    } catch {
	    }
	    return $null
	}

	function Save-MT5TerminalConfig {
	    param(
	        [string]$ConfigPath,
	        [string]$TerminalPath
	    )
	    $payload = @{ terminal_path = $TerminalPath }
	    $json = $payload | ConvertTo-Json -Depth 4
	    Set-Content -Path $ConfigPath -Value $json -Encoding UTF8
	}

	function Find-MT5Terminals {
	    param([int]$MaxResults = 25)
	    $found = New-Object System.Collections.Generic.List[string]
	    $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([StringComparer]::OrdinalIgnoreCase)

	    function Add-FoundPath {
	        param([string]$Path)
	        if ([string]::IsNullOrWhiteSpace($Path)) { return }
	        try {
	            if (-not (Test-Path -LiteralPath $Path)) { return }
	        } catch {
	            return
	        }
	        if ($seen.Add($Path)) {
	            [void]$found.Add($Path)
	        }
	    }

	    $candidates = @(
	        "C:\Program Files\MetaTrader 5\terminal64.exe",
	        "C:\Program Files (x86)\MetaTrader 5\terminal64.exe",
	        "C:\Program Files\XM Global MT5\terminal64.exe",
	        "C:\Program Files\MetaQuotes\MetaTrader 5\terminal64.exe"
	    )
	    foreach ($p in $candidates) {
	        Add-FoundPath -Path $p
	        if ($found.Count -ge $MaxResults) { return ,$found.ToArray() }
	    }

	    foreach ($base in @($env:APPDATA, $env:LOCALAPPDATA, $env:PROGRAMDATA)) {
	        if ([string]::IsNullOrWhiteSpace($base)) { continue }
	        $terminalRoot = Join-Path $base "MetaQuotes\Terminal"
	        if (-not (Test-Path -LiteralPath $terminalRoot)) { continue }
	        try {
	            foreach ($dir in Get-ChildItem -Path $terminalRoot -Directory -ErrorAction SilentlyContinue) {
	                Add-FoundPath -Path (Join-Path $dir.FullName "terminal64.exe")
	                if ($found.Count -ge $MaxResults) { return ,$found.ToArray() }
	            }
	        } catch {
	        }
	    }

	    $programRoots = @($env:ProgramW6432, $env:ProgramFiles, ${env:ProgramFiles(x86)}) |
	        Where-Object { $_ -and (Test-Path -LiteralPath $_) } |
	        Select-Object -Unique

	    foreach ($root in $programRoots) {
	        try {
	            foreach ($dir in Get-ChildItem -Path $root -Directory -ErrorAction SilentlyContinue) {
	                Add-FoundPath -Path (Join-Path $dir.FullName "terminal64.exe")
	                if ($found.Count -ge $MaxResults) { return ,$found.ToArray() }

	                $name = ([string]$dir.Name).ToLowerInvariant()
	                if ($name -match "metatrader|mt5|metaquotes") {
	                    foreach ($sub in Get-ChildItem -Path $dir.FullName -Directory -ErrorAction SilentlyContinue) {
	                        Add-FoundPath -Path (Join-Path $sub.FullName "terminal64.exe")
	                        if ($found.Count -ge $MaxResults) { return ,$found.ToArray() }
	                    }
	                }
	            }
	        } catch {
	        }
	        if ($found.Count -ge $MaxResults) { break }
	    }

	    return ,$found.ToArray()
	}

	function Configure-MT5TerminalWizard {
	    param(
	        [string]$AppDir
	    )

	    if ($env:OS -ne "Windows_NT") {
	        Write-Log "Skipping MT5 wizard (not Windows)."
	        return
	    }

	    $cfgPath = Join-Path $AppDir ".rg_terminal.json"
	    $configured = Get-ConfiguredMT5Terminal -ConfigPath $cfgPath
	    if ($configured) {
	        Write-Log "MT5 terminal already configured: $configured"
	        return
	    }

	    $interactive = $true
	    try { $interactive = -not [Console]::IsInputRedirected } catch { $interactive = $false }

	    $found = @(Find-MT5Terminals -MaxResults 25)
	    if ($found.Count -gt 0) {
	        Write-Log ("Detected MT5 terminals: " + ($found -join " | "))
	        if (-not $interactive) {
	            $pick = $found[0]
	            Save-MT5TerminalConfig -ConfigPath $cfgPath -TerminalPath $pick
	            Write-Log "Saved MT5 terminal_path to $cfgPath"
	            return
	        }

	        while ($true) {
	            Write-Output ""
	            Write-Output "MetaTrader 5 detectado. Selecione o terminal64.exe para usar:"
	            for ($i = 0; $i -lt $found.Count; $i++) {
	                Write-Output ("  [{0}] {1}" -f ($i + 1), $found[$i])
	            }
	            Write-Output "  [M] Digitar caminho manual"
	            Write-Output "  [D] Abrir página de download do MT5"
	            Write-Output "  [S] Pular (configurar depois)"

	            $choice = (Read-Host "Opção").Trim()
	            if ([string]::IsNullOrWhiteSpace($choice)) { $choice = "1" }
	            $lower = $choice.ToLowerInvariant()

	            if ($lower -eq "s") {
	                Write-Log "Skipping MT5 terminal configuration by user choice."
	                return
	            }
	            if ($lower -eq "d") {
	                try { Start-Process $MT5DownloadUrl | Out-Null } catch { }
	                continue
	            }
	            if ($lower -eq "m") {
	                $entered = (Read-Host "Caminho completo para terminal64.exe").Trim().Trim('"')
	                if (-not [string]::IsNullOrWhiteSpace($entered) -and (Test-Path -LiteralPath $entered)) {
	                    Save-MT5TerminalConfig -ConfigPath $cfgPath -TerminalPath $entered
	                    Write-Log "Saved MT5 terminal_path to $cfgPath"
	                    return
	                }
	                Write-Output "Caminho não encontrado. Tente novamente."
	                continue
	            }

	            $idx = 0
	            if ([int]::TryParse($choice, [ref]$idx) -and $idx -ge 1 -and $idx -le $found.Count) {
	                $pick = $found[$idx - 1]
	                Save-MT5TerminalConfig -ConfigPath $cfgPath -TerminalPath $pick
	                Write-Log "Saved MT5 terminal_path to $cfgPath"
	                return
	            }

	            Write-Output "Opção inválida."
	        }
	    }

	    Write-Log "MT5 terminal64.exe not found. Install MetaTrader 5: $MT5DownloadUrl"
	    if (-not $interactive) {
	        return
	    }

	    while ($true) {
	        Write-Output ""
	        Write-Output "MetaTrader 5 não encontrado. Opções:"
	        Write-Output "  [D] Abrir página de download do MT5"
	        Write-Output "  [M] Digitar caminho manual"
	        Write-Output "  [S] Pular (instalar depois)"

	        $choice = (Read-Host "Opção").Trim().ToLowerInvariant()
	        if ($choice -eq "s") { return }
	        if ($choice -eq "d") {
	            try { Start-Process $MT5DownloadUrl | Out-Null } catch { }
	            continue
	        }
	        if ($choice -eq "m" -or $choice -eq "") {
	            $entered = (Read-Host "Caminho completo para terminal64.exe").Trim().Trim('"')
	            if (-not [string]::IsNullOrWhiteSpace($entered) -and (Test-Path -LiteralPath $entered)) {
	                Save-MT5TerminalConfig -ConfigPath $cfgPath -TerminalPath $entered
	                Write-Log "Saved MT5 terminal_path to $cfgPath"
	                return
	            }
	            Write-Output "Caminho não encontrado. Tente novamente."
	            continue
	        }
	        Write-Output "Opção inválida."
	    }
	}

	try {
	    Write-Log "Setup started."

    if (-not [Environment]::Is64BitOperatingSystem) {
        Fail "Windows 64-bit is required."
    }
    if ([Environment]::OSVersion.Version.Major -lt 10) {
        Fail "Windows 10 or newer is required."
    }

    if (-not (Test-Path $AppDir)) {
        Fail "AppDir not found: $AppDir"
    }

	    if (-not (Test-Path $Requirements)) {
	        Fail "requirements.txt not found at $Requirements"
	    }

	    $configExample = Join-Path $AppDir "config.example.txt"
	    $configTxt = Join-Path $AppDir "config.txt"
	    if (-not (Test-Path -LiteralPath $configTxt) -and (Test-Path -LiteralPath $configExample)) {
	        Copy-Item -Path $configExample -Destination $configTxt -Force
	        Write-Log "Created config.txt from config.example.txt"
	    }

	    $pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-$PythonArch.exe"
	    Write-Log "Checking internet access: $pythonUrl"
	    Invoke-WebRequest -Uri $pythonUrl -Method Head -UseBasicParsing -TimeoutSec 15 | Out-Null

    if (-not $AllowUnpinned) {
        Assert-RequirementsPinned -Path $Requirements
    }

    $targetVersion = [version]$PythonVersion
    $existing = Find-Python -TargetVersion $PythonVersion
    $pythonExe = $null
    $installNeeded = $true

    if ($existing) {
        $existingVersion = [version]$existing.Version
        $targetMajorMinor = Get-TargetMajorMinor -Version $PythonVersion
        $existingMajorMinor = Get-TargetMajorMinor -Version $existing.Version
        if ($existingMajorMinor -eq $targetMajorMinor -and $existingVersion -ge $targetVersion) {
            $installNeeded = $false
            $pythonExe = $existing.Path
            Write-Log "Existing Python found: $($existing.Version) at $pythonExe"
        } else {
            Write-Log "Existing Python found ($($existing.Version)) but target is $PythonVersion. Installing target."
        }
    }

    if ($installNeeded) {
        if ($InstallAllUsers -and -not (Is-Admin)) {
            Fail "InstallAllUsers requires admin privileges."
        }

        $installerName = "python-$PythonVersion-$PythonArch.exe"
        $installerPath = Join-Path $env:TEMP $installerName

        Write-Log "Downloading Python installer: $pythonUrl"
        Invoke-WebRequest -Uri $pythonUrl -OutFile $installerPath -UseBasicParsing

        $majorMinorNoDot = ($PythonVersion.Split(".")[0..1] -join "")
        $targetDir = if ($InstallAllUsers) {
            Join-Path $env:ProgramFiles "Python$majorMinorNoDot"
        } else {
            Join-Path $env:LOCALAPPDATA "Programs\Python\Python$majorMinorNoDot"
        }

        $installArgs = @(
            "/quiet",
            "InstallAllUsers=$([int]$InstallAllUsers.IsPresent)",
            "TargetDir=$targetDir",
            "Include_pip=1",
            "PrependPath=1",
            "SimpleInstall=1",
            "Include_test=0",
            "CompileAll=0",
            "Shortcuts=0"
        )

        Write-Log "Installing Python to $targetDir"
        $proc = Start-Process -FilePath $installerPath -ArgumentList $installArgs -Wait -PassThru
        if ($proc.ExitCode -ne 0) {
            Fail "Python installer failed with exit code $($proc.ExitCode)"
        }

        $pythonExe = Resolve-InstalledPython -PreferredPath (Join-Path $targetDir "python.exe") -TargetVersion $PythonVersion -AllUsers:$InstallAllUsers
        if (-not $pythonExe) {
            Fail "python.exe not found after install. Expected under $targetDir."
        }
        Write-Log "Resolved Python at $pythonExe"
    }

    if (-not $pythonExe) {
        Fail "Python executable not resolved."
    }

    $pythonDir = Split-Path -Parent $pythonExe
    $scriptsDir = Join-Path $pythonDir "Scripts"
    $env:Path = "$pythonDir;$scriptsDir;$env:Path"

    if (Test-Path $VenvDir) {
        Write-Log "Removing existing venv at $VenvDir"
        Remove-Item -Path $VenvDir -Recurse -Force
    }

    Write-Log "Creating venv at $VenvDir"
    & $pythonExe -m venv "$VenvDir"
    if ($LASTEXITCODE -ne 0) {
        Fail "venv creation failed with exit code $LASTEXITCODE"
    }

    $venvPython = Join-Path $VenvDir "Scripts\python.exe"
    if (-not (Test-Path $venvPython)) {
        Fail "venv python.exe not found at $venvPython"
    }

    Write-Log "Upgrading pip/setuptools/wheel"
    & $venvPython -m pip install --upgrade pip setuptools wheel --no-input --disable-pip-version-check
    if ($LASTEXITCODE -ne 0) {
        Fail "pip upgrade failed with exit code $LASTEXITCODE"
    }

    Write-Log "Installing dependencies from $Requirements"
    & $venvPython -m pip install --no-cache-dir --retries 5 --timeout 30 --no-input --disable-pip-version-check -r "$Requirements"
    if ($LASTEXITCODE -ne 0) {
        Fail "pip install failed with exit code $LASTEXITCODE"
    }

    # Playwright precisa baixar o Chromium para gerar PDFs
    try {
        Write-Log "Installing Playwright Chromium (for PDF reports)"
        & $venvPython -m playwright install chromium
        if ($LASTEXITCODE -ne 0) {
            Write-Log "WARN: playwright install chromium failed with exit code $LASTEXITCODE"
        }
    } catch {
        Write-Log "WARN: playwright install chromium failed: $($_.Exception.Message)"
    }

    $pywin32Post = Join-Path $VenvDir "Scripts\pywin32_postinstall.py"
    if (Test-Path $pywin32Post) {
        Write-Log "Running pywin32 post-install"
        & $venvPython $pywin32Post -install
        if ($LASTEXITCODE -ne 0) {
            Fail "pywin32 post-install failed with exit code $LASTEXITCODE"
        }
    }

	    if (-not $SkipHealthCheck) {
	        $healthCheck = Join-Path $AppDir "health_check.py"
	        if (Test-Path $healthCheck) {
	            $logsDir = Join-Path $AppDir "logs"
	            Write-Log "Running health_check.py"
	            & $venvPython $healthCheck --app-dir "$AppDir" --logs-dir "$logsDir" --log-file "$LogFile"
	            if ($LASTEXITCODE -ne 0) {
	                Fail "health_check.py failed with exit code $LASTEXITCODE"
	            }
	        } else {
	            Write-Log "health_check.py not found. Skipping."
	        }
	    }

	    if (-not $SkipMT5Wizard) {
	        try {
	            Configure-MT5TerminalWizard -AppDir $AppDir
	        } catch {
	            Write-Log "MT5 wizard failed (non-fatal): $($_.Exception.Message)"
	        }
	    } else {
	        Write-Log "Skipping MT5 terminal wizard."
	    }

	    Write-Log "Setup completed successfully."
	    exit 0
	} catch {
    Write-Log "Setup failed: $($_.Exception.Message)"
    exit 1
}
