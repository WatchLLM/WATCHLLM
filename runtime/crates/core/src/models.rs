use serde::{Deserialize, Serialize};

/// Input provided to the kernel for a single evaluation.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KernelExecutionInput {
    /// The source code to evaluate.
    pub source: String,
    /// Language identifier (e.g., "javascript", "typescript").
    pub language: String,
    /// Optional configuration JSON string.
    pub config: Option<String>,
}

/// A single violation detected by a rule.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct KernelViolation {
    /// Human-readable description of the violation.
    pub message: String,
    /// The rule that triggered the violation.
    pub rule: String,
    /// The line number where the violation was found (1‑based).
    pub line: usize,
    /// The column number where the violation was found (1‑based).
    pub column: usize,
    /// The severity of the violation (e.g., "error", "warning").
    pub severity: String,
}

/// The payload returned inside a successful kernel result.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct KernelPayload {
    /// Whether the source is allowed (true) or blocked (false).
    pub allowed: bool,
    /// List of violations found during evaluation.
    pub violations: Vec<KernelViolation>,
}

/// The top‑level result returned by the kernel.
/// This structure must match the Python kernel output exactly.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub struct KernelExecutionResult {
    /// Execution status: "ok" for a successful run, "error" for a caught error.
    pub status: String,
    /// Exit code: 0 for allowed, 1 for blocked, 2 for internal error.
    pub exit_code: i32,
    /// The evaluation payload (present when status is "ok").
    pub payload: Option<KernelPayload>,
    /// An error message (present when status is "error").
    pub error: Option<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    /// Helper to produce a JSON string from a KernelExecutionResult.
    fn to_json(result: &KernelExecutionResult) -> String {
        serde_json::to_string(result).expect("serialization should succeed")
    }

    /// Helper to produce a pretty‑printed JSON string for snapshot comparison.
    fn to_json_pretty(result: &KernelExecutionResult) -> String {
        serde_json::to_string_pretty(result).expect("serialization should succeed")
    }

    #[test]
    fn test_serialization_parity_allowed_no_violations() {
        // This JSON must match the Python kernel output for an allowed file with no violations.
        let expected = r#"{"status":"ok","exit_code":0,"payload":{"allowed":true,"violations":[]},"error":null}"#;

        let result = KernelExecutionResult {
            status: "ok".to_string(),
            exit_code: 0,
            payload: Some(KernelPayload {
                allowed: true,
                violations: vec![],
            }),
            error: None,
        };

        let json = to_json(&result);
        assert_eq!(json, expected);
    }

    #[test]
    fn test_serialization_parity_blocked_with_violations() {
        // This JSON must match the Python kernel output for a blocked file with two violations.
        let expected = r#"{"status":"ok","exit_code":1,"payload":{"allowed":false,"violations":[{"message":"Hardcoded secret found","rule":"secrets","line":12,"column":5,"severity":"error"},{"message":"Forbidden import: fs","rule":"imports","line":3,"column":1,"severity":"error"}]},"error":null}"#;

        let result = KernelExecutionResult {
            status: "ok".to_string(),
            exit_code: 1,
            payload: Some(KernelPayload {
                allowed: false,
                violations: vec![
                    KernelViolation {
                        message: "Hardcoded secret found".to_string(),
                        rule: "secrets".to_string(),
                        line: 12,
                        column: 5,
                        severity: "error".to_string(),
                    },
                    KernelViolation {
                        message: "Forbidden import: fs".to_string(),
                        rule: "imports".to_string(),
                        line: 3,
                        column: 1,
                        severity: "error".to_string(),
                    },
                ],
            }),
            error: None,
        };

        let json = to_json(&result);
        assert_eq!(json, expected);
    }

    #[test]
    fn test_serialization_parity_internal_error() {
        // This JSON must match the Python kernel output for an internal error.
        let expected = r#"{"status":"error","exit_code":2,"payload":null,"error":"Parser error: unexpected token"}"#;

        let result = KernelExecutionResult {
            status: "error".to_string(),
            exit_code: 2,
            payload: None,
            error: Some("Parser error: unexpected token".to_string()),
        };

        let json = to_json(&result);
        assert_eq!(json, expected);
    }

    #[test]
    fn test_deserialization_roundtrip() {
        let original = KernelExecutionResult {
            status: "ok".to_string(),
            exit_code: 0,
            payload: Some(KernelPayload {
                allowed: true,
                violations: vec![KernelViolation {
                    message: "test".to_string(),
                    rule: "test_rule".to_string(),
                    line: 1,
                    column: 1,
                    severity: "warning".to_string(),
                }],
            }),
            error: None,
        };

        let json = to_json(&original);
        let parsed: KernelExecutionResult =
            serde_json::from_str(&json).expect("deserialization should succeed");
        assert_eq!(original, parsed);
    }

    #[test]
    fn test_pretty_print_does_not_affect_parity() {
        // Ensure that pretty‑printed JSON still contains the same data.
        let result = KernelExecutionResult {
            status: "ok".to_string(),
            exit_code: 0,
            payload: Some(KernelPayload {
                allowed: true,
                violations: vec![],
            }),
            error: None,
        };

        let pretty = to_json_pretty(&result);
        let parsed: KernelExecutionResult =
            serde_json::from_str(&pretty).expect("deserialization should succeed");
        assert_eq!(result, parsed);
    }
}
