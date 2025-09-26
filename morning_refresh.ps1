$site = "C:\Users\strol\OneDrive\Desktop\Trading - Desktop\00_Scripts\Website"
$py   = "C:\Users\strol\AppData\Local\Programs\Python\Python313\python.exe"
$port = 8000

# 1) Update all JSON + snapshots
& $py "$site\update_dashboard.py" $site

# 2) Start server if not already running
$up = (Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded
if (-not $up) {
  Start-Process -FilePath $py -ArgumentList "-m http.server $port" -WorkingDirectory $site -WindowStyle Minimized
  Start-Sleep -Seconds 2
}

# 3) Open the dashboard
Start-Process "http://localhost:$port/"
