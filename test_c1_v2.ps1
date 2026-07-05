
$ErrorActionPreference = "Stop"

echo "=== Starting Replay Server ==="
cd replay/src/server
$process = Start-Process node -ArgumentList "index.cjs" -PassThru -WindowStyle Hidden

cd ../../..
Start-Sleep -Seconds 5

$env:WATCHLLM_REPLAY_URL="http://localhost:3001"
$env:WATCHLLM_TRACE_ID="c-test-trace-123"

# evaluate (should block and post to replay)
$exitCode = 0
try {
    & watchllm evaluate payments/test.ts
    $exitCode = $LASTEXITCODE
} catch {
    $exitCode = 1
}

if ($exitCode -eq 0) {
    Stop-Process -Id $process.Id -Force
    throw "Should have blocked"
}

Start-Sleep -Seconds 2

# Fetch from API to see if it recorded
$response = Invoke-RestMethod -Uri "http://localhost:3001/api/violations"
if ($response.Count -eq 0) {
    Stop-Process -Id $process.Id -Force
    throw "C2 Failed: No violations returned"
}

$first = $response[0]
if ($first.run_id -ne "c-test-trace-123") {
    Stop-Process -Id $process.Id -Force
    throw "C2 Failed: Trace ID mismatch"
}

if ($first.report.decision -ne "BLOCK") {
    Stop-Process -Id $process.Id -Force
    throw "C2 Failed: Decision mismatch"
}

Stop-Process -Id $process.Id -Force
echo "C1 & C2 Passed!"

