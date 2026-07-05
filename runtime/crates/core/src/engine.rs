use std::convert::TryFrom;

use crate::models::{KernelExecutionResult, KernelPayload, KernelViolation};
use crate::parser::{parse_source, SourceLanguage};
use crate::rules::auth_flow::check_auth_flow;
use crate::rules::boundaries::check_boundaries;
use crate::rules::imports::{find_forbidden_imports_in_tree, DEFAULT_FORBIDDEN_MODULES};
use crate::rules::secrets::find_secret_literals_in_tree;
use crate::rules::RuleError;

pub fn evaluate_source(source: &str, language: SourceLanguage) -> KernelExecutionResult {
    match collect_violations(source, language) {
        Ok(violations) => ok_result(violations),
        Err(message) => error_result(message),
    }
}

pub fn evaluate_source_with_language_name(source: &str, language: &str) -> KernelExecutionResult {
    let parsed_language = match SourceLanguage::try_from(language) {
        Ok(language) => language,
        Err(err) => return error_result(format!("Parser error: {:?}", err)),
    };

    evaluate_source(source, parsed_language)
}

fn collect_violations(
    source: &str,
    language: SourceLanguage,
) -> Result<Vec<KernelViolation>, String> {
    let tree = parse_source(source, language)
        .map_err(|err| format!("Parser error: {:?}", err))?;

    let mut violations = Vec::new();

    append_rule_violations(
        &mut violations,
        find_secret_literals_in_tree(source, language, &tree),
        "secrets",
    )?;

    append_rule_violations(
        &mut violations,
        find_forbidden_imports_in_tree(source, language, &tree, DEFAULT_FORBIDDEN_MODULES),
        "imports",
    )?;

    append_rule_violations(
        &mut violations,
        check_boundaries(source, language),
        "boundaries",
    )?;

    append_rule_violations(
        &mut violations,
        check_auth_flow(source, language),
        "auth_flow",
    )?;

    Ok(violations)
}

fn append_rule_violations(
    target: &mut Vec<KernelViolation>,
    result: Result<Vec<KernelViolation>, RuleError>,
    rule_name: &str,
) -> Result<(), String> {
    match result {
        Ok(mut violations) => {
            target.append(&mut violations);
            Ok(())
        }
        Err(err) => Err(format!("{} rule error: {:?}", rule_name, err)),
    }
}

fn ok_result(violations: Vec<KernelViolation>) -> KernelExecutionResult {
    let allowed = violations.is_empty();

    KernelExecutionResult {
        status: "ok".to_string(),
        exit_code: if allowed { 0 } else { 1 },
        payload: Some(KernelPayload {
            allowed,
            violations,
        }),
        error: None,
    }
}

fn error_result(message: String) -> KernelExecutionResult {
    KernelExecutionResult {
        status: "error".to_string(),
        exit_code: 2,
        payload: None,
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

        let result = evaluate_source(source, SourceLanguage::TypeScript);

        assert_eq!(result.status, "ok");
        assert_eq!(result.exit_code, 0);
        assert!(result.error.is_none());

        let payload = result.payload.as_ref().expect("payload should exist");
        assert!(payload.allowed);
        assert!(payload.violations.is_empty());
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

        let result = evaluate_source(source, SourceLanguage::TypeScript);

        assert_eq!(result.status, "ok");
        assert_eq!(result.exit_code, 1);
        assert!(result.error.is_none());

        let payload = result.payload.as_ref().expect("payload should exist");
        assert!(!payload.allowed);
        assert_eq!(payload.violations.len(), 4);

        let rules: Vec<&str> = payload
            .violations
            .iter()
            .map(|violation| violation.rule.as_str())
            .collect();

        assert!(rules.contains(&"secrets"));
        assert!(rules.contains(&"imports"));
        assert!(rules.contains(&"boundaries"));
        assert!(rules.contains(&"auth_flow"));
    }

    #[test]
    fn engine_result_is_json_serializable() {
        let source = r#"
            const value = "safe";
        "#;

        let result = evaluate_source(source, SourceLanguage::TypeScript);
        let json = serde_json::to_string(&result).unwrap();

        assert!(json.contains(r#""status":"ok""#));
        assert!(json.contains(r#""exit_code":0"#));
        assert!(json.contains(r#""payload""#));
        assert!(json.contains(r#""allowed":true"#));
        assert!(json.contains(r#""violations":[]"#));
    }

    #[test]
    fn unsupported_language_returns_error_result() {
        let result = evaluate_source_with_language_name("print('hello')", "python");

        assert_eq!(result.status, "error");
        assert_eq!(result.exit_code, 2);
        assert!(result.payload.is_none());
        assert!(result.error.unwrap().contains("UnsupportedLanguage"));
    }
}
