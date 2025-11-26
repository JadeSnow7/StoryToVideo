Get-Content .env | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#")) {
        $name, $value = $line -split '=', 2
        [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
}

.\frpc.exe -c .\frpc_worker.toml