
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force -Path payments | Out-Null
Set-Content -Path payments/test.ts -Value "import * as stripe from 'stripe';"

echo "Testing normal evaluate (should BLOCK)"
$exitCode = 0
try {
    # run watchllm evaluate directly, store exit code
    & watchllm evaluate payments/test.ts
    $exitCode = $LASTEXITCODE
} catch {
    $exitCode = 1
}

if ($exitCode -eq 0) {
    throw "Should have blocked, but allowed"
}
echo "Blocked successfully"

echo "Testing spawned evaluate with token (should ALLOW)"
& watchllm spawn --role read-only-agent --command "watchllm evaluate payments/test.ts"
if ($LASTEXITCODE -ne 0) {
    throw "Should have allowed"
}
echo "B1 Passed"

