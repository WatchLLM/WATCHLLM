use std::convert::TryFrom;

use crate::models::{KernelExecutionResult, KernelViolation, Location, RuleResult};
use crate::parser::{parse_source, SourceLanguage};
use crate::rules::auth_flow::check_auth_flow;
use crate::rules::boundaries::check_boundaries;
use crate::rules::imports::{find_forbidden_imports_in_tree, DEFAULT_FORBIDDEN_MODULES};
use crate::rules::secrets::find_secret_literals_in_tree;
use crate::rules::RuleError;

pub const ENFORCE_MODE: &str = "enforce";
pub const SHADOW_MODE: &str = "shadow";

pub fn evaluate_source(
    source: &str,
    language: SourceLanguage,
    file_path: Option<&str>,
    mode: &str,
) -> KernelExecutionResult {
    match evaluate_all_rules(source, language) {
        Ok(rule_results) => build_result(rule_results, file_path, language, mode),
        Err(message) => error_result(message, file_path, &language_name(&language)),
    }
}

pub fn evaluate_source_with_language_name(
    source: &str,
    language: &str,
    file_path: Option<&str>,
    mode: &str,
) -> KernelExecutionResult {
    let parsed_language = match SourceLanguage::try_from(language) {
        Ok(language) => language,
        Err(err) => return error_result(format!("Parser error: {:?}", err), file_path, language),
    };

    evaluate_source(source, parsed_language, file_path, mode)
}

fn evaluate_all_rules(source: &str, language: SourceLanguage) -> Result<Vec<RuleResult>, String> {
    let tree = parse_source(source, language).map_err(|err| format!("Parser error: {:?}", err))?;

    let mut rule_results = Vec::new();

    rule_results.push(eval_rule(
        "watchllm-rule-secrets",
        find_secret_literals_in_tree(source, language, &tree),
    ));

    rule_results.push(eval_rule(
        "watchllm-rule-imports",
        find_forbidden_imports_in_tree(source, language, &tree, DEFAULT_FORBIDDEN_MODULES),
    ));

    rule_results.push(eval_rule(
        "watchllm-rule-boundaries",
        check_boundaries(source, language),
    ));

    rule_results.push(eval_rule(
        "watchllm-rule-auth",
        check_auth_flow(source, language),
    ));

    Ok(rule_results)
}

fn eval_rule(rule_id: &str, result: Result<Vec<KernelViolation>, RuleError>) -> RuleResult {
    match result {
        Ok(violations) => {
            let status = if violations.is_empty() {
                "PASS"
            } else {
                "FAIL"
            };
            RuleResult {
                rule_id: rule_id.to_string(),
                status: status.to_string(),
                violations,
            }
        }
        Err(err) => RuleResult {
            rule_id: rule_id.to_string(),
            status: "FAIL".to_string(),
            violations: vec![KernelViolation {
                rule_id: rule_id.to_string(),
                message: format!("Rule error: {:?}", err),
                location: Location {
                    line: 0,
                    column: 0,
                    end_line: None,
                    end_column: None,
                },
                severity: "HIGH".to_string(),
                evidence: String::new(),
            }],
        },
    }
}

fn build_result(
    rule_results: Vec<RuleResult>,
    file_path: Option<&str>,
    language: SourceLanguage,
    mode: &str,
) -> KernelExecutionResult {
    let has_failure = rule_results.iter().any(|r| r.status == "FAIL");
    let decision = if mode == SHADOW_MODE {
        "ALLOW"
    } else if has_failure {
        "BLOCK"
    } else {
        "ALLOW"
    };

    KernelExecutionResult {
        decision: decision.to_string(),
        mode: mode.to_string(),
        file_path: file_path.map(|s| s.to_string()),
        language: language_name(&language),
        rule_results,
        error: None,
    }
}

fn language_name(language: &SourceLanguage) -> String {
    match language {
        SourceLanguage::JavaScript => "javascript".to_string(),
        SourceLanguage::TypeScript => "typescript".to_string(),
        SourceLanguage::Tsx => "tsx".to_string(),
    }
}

fn error_result(message: String, file_path: Option<&str>, language: &str) -> KernelExecutionResult {
    KernelExecutionResult {
        decision: "ALLOW".to_string(),
        mode: "enforce".to_string(),
        file_path: file_path.map(|s| s.to_string()),
        language: language.to_string(),
        rule_results: vec![],
        error: Some(message),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn evaluates_allowed_typescript_source() {
        let source = r#"
            import express from "express";

            const message = "hello";

            function handler() {
                auth.verify(token);
                db.query("SELECT 1");
            }
        "#;

        let result = evaluate_source(source, SourceLanguage::TypeScript, None, ENFORCE_MODE);

        assert_eq!(result.decision, "ALLOW");
        assert_eq!(result.exit_code(), 0);
        assert!(result.error.is_none());
        assert_eq!(result.rule_results.len(), 4);
        for rr in &result.rule_results {
            assert_eq!(rr.status, "PASS");
        }
    }

    #[test]
    fn aggregates_multiple_rule_violations() {
        let source = r#"
            import childProcess from "child_process";
            import { connect } from "@internal/db";

            const apiKey = "sk_live_123";

            function handler() {
                db.query("SELECT 1");
                auth.verify(token);
            }
        "#;

        let result = evaluate_source(source, SourceLanguage::TypeScript, None, ENFORCE_MODE);

        assert_eq!(result.decision, "BLOCK");
        assert_eq!(result.exit_code(), 1);
        assert!(result.error.is_none());
        assert_eq!(result.rule_results.len(), 4);

        let failing: Vec<&RuleResult> = result
            .rule_results
            .iter()
            .filter(|r| r.status == "FAIL")
            .collect();
        assert_eq!(failing.len(), 4);

        let rule_ids: Vec<&str> = failing.iter().map(|r| r.rule_id.as_str()).collect();
        assert!(rule_ids.contains(&"watchllm-rule-secrets"));
        assert!(rule_ids.contains(&"watchllm-rule-imports"));
        assert!(rule_ids.contains(&"watchllm-rule-boundaries"));
        assert!(rule_ids.contains(&"watchllm-rule-auth"));
    }

    #[test]
    fn shadow_mode_always_allows() {
        let source = r#"
            import childProcess from "child_process";
            const apiKey = "sk_live_123";
        "#;

        let result = evaluate_source(source, SourceLanguage::TypeScript, None, SHADOW_MODE);

        assert_eq!(result.decision, "ALLOW");
        assert_eq!(result.exit_code(), 0);
        let failing: Vec<&RuleResult> = result
            .rule_results
            .iter()
            .filter(|r| r.status == "FAIL")
            .collect();
        assert!(
            failing.len() >= 2,
            "shadow mode should preserve failing rules"
        );
    }

    #[test]
    fn engine_result_is_json_serializable() {
        let source = r#"
            const value = "safe";
        "#;

        let result = evaluate_source(source, SourceLanguage::TypeScript, None, ENFORCE_MODE);
        let json = serde_json::to_string(&result).unwrap();

        assert!(json.contains(r#""decision":"ALLOW""#));
        assert!(json.contains(r#""mode":"enforce""#));
        assert!(json.contains(r#""rule_results""#));
    }

    #[test]
    fn unsupported_language_returns_error_result() {
        let result =
            evaluate_source_with_language_name("print('hello')", "python", None, ENFORCE_MODE);

        assert!(result.error.is_some());
        assert_eq!(result.exit_code(), 2);
    }

    #[test]
    fn file_path_is_reflected_in_result() {
        let source = "const x = 1;";
        let result = evaluate_source(
            source,
            SourceLanguage::TypeScript,
            Some("src/app.ts"),
            ENFORCE_MODE,
        );

        assert_eq!(result.file_path.as_deref(), Some("src/app.ts"));
    }

    #[test]
    fn language_is_reflected_in_result() {
        let source = "const x = 1;";
        let result = evaluate_source(source, SourceLanguage::JavaScript, None, ENFORCE_MODE);

        assert_eq!(result.language, "javascript");
    }
}
