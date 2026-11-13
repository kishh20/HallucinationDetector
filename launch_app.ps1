# Hallucination Detector Desktop App Launcher
$projectDir = "C:\Users\KISHOR SRE\OneDrive\HallucinationProject"
Set-Location $projectDir

function Get-ActivePort {
    foreach ($p in 8001, 8000, 8080) {
        try {
            $tcp = New-Object System.Net.Sockets.TcpClient
            $async = $tcp.BeginConnect("127.0.0.1", $p, $null, $null)
            $success = $async.AsyncWaitHandle.WaitOne(400, $false)
            if ($success -and $tcp.Connected) {
                $tcp.EndConnect($async)
                $tcp.Close()
                return $p
            }
            $tcp.Close()
        } catch {}
    }
    return $null
}

$port = Get-ActivePort

if (-not $port) {
    # Start server in background
    $pythonw = "C:\Users\KISHOR SRE\AppData\Local\Python\pythoncore-3.14-64\pythonw.exe"
    if (-not (Test-Path $pythonw)) {
        $pythonw = "pythonw.exe"
    }
    Start-Process -FilePath $pythonw -ArgumentList "server.py" -WorkingDirectory $projectDir -WindowStyle Hidden
    
    # Wait up to 8 seconds for server to start
    for ($i = 0; $i -lt 16; $i++) {
        Start-Sleep -Milliseconds 500
        $port = Get-ActivePort
        if ($port) { break }
    }
}

if (-not $port) {
    $port = 8001
}

$url = "http://localhost:$port"

# Find browser for --app mode (Edge or Chrome)
$edgePath = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edgePath)) {
    $edgePath = "${env:ProgramFiles}\Microsoft\Edge\Application\msedge.exe"
}
$chromePath = "${env:ProgramFiles}\Google\Chrome\Application\chrome.exe"
if (-not (Test-Path $chromePath)) {
    $chromePath = "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe"
}

$appArgs = "--app=$url --app-id=hallucination-detector"

if (Test-Path $edgePath) {
    Start-Process -FilePath $edgePath -ArgumentList $appArgs
} elseif (Test-Path $chromePath) {
    Start-Process -FilePath $chromePath -ArgumentList $appArgs
} else {
    Start-Process -FilePath $url
}
