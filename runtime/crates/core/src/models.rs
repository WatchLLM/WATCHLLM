use serde::{Deserialize, Serialize};

/// Source code location range.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct Location {
    pub line: usize,
    pub column: usize,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub end_line: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub end_column: Option<usize>,
}

/// A single violation detected by a rule.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct KernelViolation {
    pub rule_id: String,
    pub message: String,
    pub location: Location,
    pub severity: String,
    pub evidence: String,
}

/// Result for a single rule evaluation.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct RuleResult {
    pub rule_id: String,
    pub status: String,
    pub violations: Vec<KernelViolation>,
}

/// The top-level result returned by the kernel.
/// This structure must match the Python kernel output exactly.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct KernelExecutionResult {
    pub decision: String,
    pub mode: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub file_path: Option<String>,
    pub language: String,
    pub rule_results: Vec<RuleResult>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub error: Option<String>,
}

impl KernelExecutionResult {
    pub fn exit_code(&self) -> i32 {
        if self.error.is_some() {
            2
        } else if self.decision == "BLOCK" {
            1
        } else {
            0
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn to_json(result: &KernelExecutionResult) -> String {
        serde_json::to_string(result).expect("serialization should succeed")
    }

    #[test]
    fn test_serialization_allowed_no_violations() {
        let expected = r#"{"decision":"ALLOW","mode":"enforce","file_path":"/tmp/test.js","language":"javascript","rule_results":[{"rule_id":"watchllm-rule-secrets","status":"PASS","violations":[]},{"rule_id":"watchllm-rule-imports","status":"PASS","violations":[]}]}"#;

        let result = KernelExecutionResult {
            decision: "ALLOW".to_string(),
            mode: "enforce".to_string(),
            file_path: Some("/tmp/test.js".to_string()),
            language: "javascript".to_string(),
            rule_results: vec![
                RuleResult {
                    rule_id: "watchllm-rule-secrets".to_string(),
                    status: "PASS".to_string(),
                    violations: vec![],
                },
                RuleResult {
                    rule_id: "watchllm-rule-imports".to_string(),
                    status: "PASS".to_string(),
                    violations: vec![],
                },
            ],
            error: None,
        };

        assert_eq!(to_json(&result), expected);
    }

    #[test]
    fn test_serialization_blocked_with_violations() {
        let expected = r#"{"decision":"BLOCK","mode":"enforce","file_path":"/tmp/test.js","language":"typescript","rule_results":[{"rule_id":"watchllm-rule-secrets","status":"FAIL","violations":[{"rule_id":"watchllm-rule-secrets","message":"Hardcoded secret found","location":{"line":12,"column":5},"severity":"HIGH","evidence":"sk_live_xxx"}]},{"rule_id":"watchllm-rule-imports","status":"FAIL","violations":[{"rule_id":"watchllm-rule-imports","message":"Forbidden import: child_process","location":{"line":3,"column":1},"severity":"HIGH","evidence":"child_process"}]}]}"#;

        let result = KernelExecutionResult {
            decision: "BLOCK".to_string(),
            mode: "enforce".to_string(),
            file_path: Some("/tmp/test.js".to_string()),
            language: "typescript".to_string(),
            rule_results: vec![
                RuleResult {
                    rule_id: "watchllm-rule-secrets".to_string(),
                    status: "FAIL".to_string(),
                    violations: vec![KernelViolation {
                        rule_id: "watchllm-rule-secrets".to_string(),
                        message: "Hardcoded secret found".to_string(),
                        location: Location {
                            line: 12,
                            column: 5,
                            end_line: None,
                            end_column: None,
                        },
                        severity: "HIGH".to_string(),
                        evidence: "sk_live_xxx".to_string(),
                    }],
                },
                RuleResult {
                    rule_id: "watchllm-rule-imports".to_string(),
                    status: "FAIL".to_string(),
                    violations: vec![KernelViolation {
                        rule_id: "watchllm-rule-imports".to_string(),
                        message: "Forbidden import: child_process".to_string(),
                        location: Location {
                            line: 3,
                            column: 1,
                            end_line: None,
                            end_column: None,
                        },
                        severity: "HIGH".to_string(),
                        evidence: "child_process".to_string(),
                    }],
                },
            ],
            error: None,
        };

        assert_eq!(to_json(&result), expected);
    }

    #[test]
    fn test_serialization_internal_error() {
        let expected = r#"{"decision":"ALLOW","mode":"enforce","language":"javascript","rule_results":[],"error":"Parser error: unexpected token"}"#;

        let result = KernelExecutionResult {
            decision: "ALLOW".to_string(),
            mode: "enforce".to_string(),
            file_path: None,
            language: "javascript".to_string(),
            rule_results: vec![],
            error: Some("Parser error: unexpected token".to_string()),
        };

        assert_eq!(to_json(&result), expected);
    }

    #[test]
    fn test_serialization_shadow_mode() {
        let expected = r#"{"decision":"ALLOW","mode":"shadow","file_path":"/tmp/test.js","language":"typescript","rule_results":[{"rule_id":"watchllm-rule-secrets","status":"FAIL","violations":[{"rule_id":"watchllm-rule-secrets","message":"Hardcoded secret found","location":{"line":12,"column":5},"severity":"HIGH","evidence":"sk_live_xxx"}]}]}"#;

        let result = KernelExecutionResult {
            decision: "ALLOW".to_string(),
            mode: "shadow".to_string(),
            file_path: Some("/tmp/test.js".to_string()),
            language: "typescript".to_string(),
            rule_results: vec![RuleResult {
                rule_id: "watchllm-rule-secrets".to_string(),
                status: "FAIL".to_string(),
                violations: vec![KernelViolation {
                    rule_id: "watchllm-rule-secrets".to_string(),
                    message: "Hardcoded secret found".to_string(),
                    location: Location {
                        line: 12,
                        column: 5,
                        end_line: None,
                        end_column: None,
                    },
                    severity: "HIGH".to_string(),
                    evidence: "sk_live_xxx".to_string(),
                }],
            }],
            error: None,
        };

        assert_eq!(to_json(&result), expected);
    }

    #[test]
    fn test_exit_code_mapping() {
        let allowed = KernelExecutionResult {
            decision: "ALLOW".to_string(),
            mode: "enforce".to_string(),
            file_path: None,
            language: "javascript".to_string(),
            rule_results: vec![],
            error: None,
        };
        assert_eq!(allowed.exit_code(), 0);

        let blocked = KernelExecutionResult {
            decision: "BLOCK".to_string(),
            mode: "enforce".to_string(),
            file_path: None,
            language: "javascript".to_string(),
            rule_results: vec![],
            error: None,
        };
        assert_eq!(blocked.exit_code(), 1);

        let errored = KernelExecutionResult {
            decision: "ALLOW".to_string(),
            mode: "enforce".to_string(),
            file_path: None,
            language: "javascript".to_string(),
            rule_results: vec![],
            error: Some("fail".to_string()),
        };
        assert_eq!(errored.exit_code(), 2);
    }

    #[test]
    fn test_deserialization_roundtrip() {
        let original = KernelExecutionResult {
            decision: "BLOCK".to_string(),
            mode: "enforce".to_string(),
            file_path: Some("test.ts".to_string()),
            language: "typescript".to_string(),
            rule_results: vec![RuleResult {
                rule_id: "watchllm-rule-secrets".to_string(),
                status: "FAIL".to_string(),
                violations: vec![KernelViolation {
                    rule_id: "watchllm-rule-secrets".to_string(),
                    message: "test".to_string(),
                    location: Location {
                        line: 1,
                        column: 1,
                        end_line: Some(1),
                        end_column: Some(10),
                    },
                    severity: "HIGH".to_string(),
                    evidence: "test".to_string(),
                }],
            }],
            error: None,
        };

        let json = to_json(&original);
        let parsed: KernelExecutionResult =
            serde_json::from_str(&json).expect("deserialization should succeed");
        assert_eq!(original, parsed);
    }
}
