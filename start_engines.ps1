$engines = @(
    @{Name = "api-gateway"; Port = 8000 },
    @{Name = "login-register-engine"; Port = 8001 },
    @{Name = "identity-engine"; Port = 8002 },
    @{Name = "raw-data-store"; Port = 8003 },
    @{Name = "metadata-engine"; Port = 8004 },
    @{Name = "processed-user-metadata-store"; Port = 8005 },
    @{Name = "vector-database"; Port = 8006 },
    @{Name = "neural-network-engine"; Port = 8007 },
    @{Name = "anomaly-detection-engine"; Port = 8008 },
    @{Name = "chunks-engine"; Port = 8010 },
    @{Name = "policy-fetching-engine"; Port = 8011 },
    @{Name = "json-user-info-generator"; Port = 8012 },
    @{Name = "analytics-warehouse"; Port = 8013 },
    @{Name = "dashboard-interface"; Port = 8014 },
    @{Name = "eligibility-rules-engine"; Port = 8015 },
    @{Name = "deadline-monitoring-engine"; Port = 8016 },
    @{Name = "simulation-engine"; Port = 8017 },
    @{Name = "government-data-sync-engine"; Port = 8018 },
    @{Name = "trust-scoring-engine"; Port = 8019 },
    @{Name = "speech-interface-engine"; Port = 8020 },
    @{Name = "document-understanding-engine"; Port = 8021 }
)

foreach ($e in $engines) {
    Start-Job -Name $e.Name -ScriptBlock {
        param($n, $p)
        Set-Location $using:PWD
        uvicorn "$n.main:app" --port $p
    } -ArgumentList $e.Name, $e.Port
}

Get-Job | Format-Table Name, State
Write-Host "Engines started. Waiting to keep they alive..."
Get-Job | Wait-Job
