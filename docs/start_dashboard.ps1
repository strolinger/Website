$website = "C:\Users\strol\OneDrive\Desktop\Trading - Desktop\00_Scripts\Website"
$python  = "C:\Users\strol\AppData\Local\Programs\Python\Python313\python.exe"
$port    = 8000

# Start the local web server if port 8000 isn't already serving
$up = (Test-NetConnection -ComputerName 127.0.0.1 -Port $port -WarningAction SilentlyContinue).TcpTestSucceeded
if (-not $up) {
  Start-Process -FilePath $python -ArgumentList "-m http.server $port" -WorkingDirectory $website -WindowStyle Minimized
  Start-Sleep -Seconds 2
}

# Open your dashboard in the default browser
Start-Process "http://localhost:$port/"
