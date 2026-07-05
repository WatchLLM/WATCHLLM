function evaluate_source(source, configJson) {
    const config = JSON.parse(configJson);
    
    // Simulate engine behavior
    if (source.includes("sk_live_")) {
        return JSON.stringify({
            status: "completed",
            exit_code: 1,
            payload: null,
            decision: "BLOCK",
            file_path: null,
            language: config.language,
            mode: "enforce",
            rule_results: [{
                rule_id: "SECRET_LITERAL",
                decision: "FAIL",
                violations: [{
                    rule_id: "SECRET_LITERAL",
                    message: "Hardcoded secret detected",
                    severity: "HIGH",
                    evidence: "sk_live_123"
                }]
            }]
        });
    }

    return JSON.stringify({
        status: "completed",
        exit_code: 0,
        payload: null,
        decision: "ALLOW",
        file_path: null,
        language: config.language,
        mode: "enforce",
        rule_results: []
    });
}

module.exports = { evaluate_source };
