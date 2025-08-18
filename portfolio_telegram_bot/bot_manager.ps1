# bot_manager.ps1 - Portfolio Telegram Bot Manager

param(
    [Parameter()]
    [ValidateSet("start", "stop", "status", "restart")]
    [string]$Action = "status"
)

function Write-ColoredText {
    param($Text, $Color = "White")
    Write-Host $Text -ForegroundColor $Color
}

function Get-BotProcesses {
    $pythonProcesses = Get-Process -Name "pythonw", "python" -ErrorAction SilentlyContinue
    $botProcesses = @()
    
    foreach ($process in $pythonProcesses) {
        try {
            $commandLine = (Get-WmiObject Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
            if ($commandLine -like "*main.py*") {
                $botProcesses += $process
            }
        } catch {
            # Ignore errors when getting command line
        }
    }
    
    return $botProcesses
}

function Start-Bot {
    Write-ColoredText "Starting Portfolio Telegram Bot..." "Green"
    
    # Check Python availability
    try {
        $pythonVersion = python --version 2>&1
        Write-ColoredText "Python found: $pythonVersion" "Gray"
    } catch {
        Write-ColoredText "Error: Python not found" "Red"
        return
    }
    
    # Check main.py exists
    if (-not (Test-Path "main.py")) {
        Write-ColoredText "Error: main.py not found in current directory" "Red"
        return
    }
    
    # Check if bot is already running
    $processes = Get-BotProcesses
    if ($processes.Count -gt 0) {
        Write-ColoredText "Bot is already running (PID: $($processes.Id -join ', '))" "Yellow"
        return
    }
    
    # Start the bot
    try {
        $process = Start-Process -FilePath "pythonw.exe" -ArgumentList "main.py" -WindowStyle Hidden -PassThru
        Start-Sleep -Seconds 3
        
        # Check if process is still running
        if (Get-Process -Id $process.Id -ErrorAction SilentlyContinue) {
            Write-ColoredText "Bot started successfully (PID: $($process.Id))" "Green"
            Write-ColoredText "Check Telegram to confirm bot is working" "Cyan"
            Write-ColoredText "To stop: .\bot_manager.ps1 stop" "Gray"
        } else {
            Write-ColoredText "Failed to start bot" "Red"
        }
    } catch {
        Write-ColoredText "Error starting bot: $($_.Exception.Message)" "Red"
    }
}

function Stop-Bot {
    Write-ColoredText "Stopping Portfolio Telegram Bot..." "Yellow"
    
    $processes = Get-BotProcesses
    
    if ($processes.Count -eq 0) {
        Write-ColoredText "No bot processes found" "Gray"
        return
    }
    
    foreach ($process in $processes) {
        Write-ColoredText "Stopping process PID: $($process.Id)" "Gray"
        try {
            Stop-Process -Id $process.Id -Force -ErrorAction Stop
        } catch {
            Write-ColoredText "Failed to stop process $($process.Id)" "Red"
        }
    }
    
    Start-Sleep -Seconds 2
    
    # Verify processes stopped
    $remainingProcesses = Get-BotProcesses
    if ($remainingProcesses.Count -eq 0) {
        Write-ColoredText "Bot stopped successfully" "Green"
    } else {
        Write-ColoredText "Some processes may still be running" "Yellow"
    }
}

function Show-Status {
    Write-ColoredText "Portfolio Telegram Bot Status" "Cyan"
    Write-Host ("=" * 50)
    
    # Check processes
    $processes = Get-BotProcesses
    
    if ($processes.Count -gt 0) {
        Write-ColoredText "Status: Running" "Green"
        Write-Host ""
        Write-ColoredText "Active processes:" "White"
        foreach ($process in $processes) {
            $startTime = if ($process.StartTime) { $process.StartTime.ToString("yyyy-MM-dd HH:mm:ss") } else { "Unknown" }
            Write-Host "  PID: $($process.Id) | Name: $($process.ProcessName) | Started: $startTime" -ForegroundColor Gray
        }
    } else {
        Write-ColoredText "Status: Not running" "Red"
    }
    
    Write-Host ""
    
    # Check logs
    if (Test-Path "logs") {
        Write-ColoredText "Recent log entries:" "White"
        $logFiles = Get-ChildItem "logs\*.log" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        
        if ($logFiles) {
            try {
                $lastLines = Get-Content $logFiles.FullName -Tail 3 -ErrorAction SilentlyContinue
                foreach ($line in $lastLines) {
                    Write-Host "  $line" -ForegroundColor Gray
                }
            } catch {
                Write-ColoredText "  Cannot read log file" "Gray"
            }
        } else {
            Write-ColoredText "  No log files found" "Gray"
        }
    } else {
        Write-ColoredText "  Logs directory not found" "Gray"
    }
    
    Write-Host ""
    Write-ColoredText "Tip: Send /status command to bot in Telegram" "Cyan"
}

function Restart-Bot {
    Write-ColoredText "Restarting Portfolio Telegram Bot..." "Blue"
    Stop-Bot
    Start-Sleep -Seconds 3
    Start-Bot
}

# Main logic
switch ($Action) {
    "start" { Start-Bot }
    "stop" { Stop-Bot }
    "status" { Show-Status }
    "restart" { Restart-Bot }
}

Write-Host ""
Write-ColoredText "Usage: .\bot_manager.ps1 [start|stop|status|restart]" "Gray"