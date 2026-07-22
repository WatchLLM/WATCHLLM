use std::collections::HashSet;

use tree_sitter::{Query, QueryCursor, Tree};

use crate::models::{KernelViolation, Location};
use crate::parser::{parse_source, SourceLanguage};

use super::RuleError;

const IMPORT_QUERY: &str = r#"
(import_statement
  source: (string) @module)

(call_expression
  function: (identifier) @callee
  arguments: (arguments (string) @module))
"#;

pub const DEFAULT_FORBIDDEN_MODULES: &[&str] = &["child_process", "vm"];

pub const ELEVATED_RISK_MODULES: &[&str] = &[
    "cluster",
    "dgram",
    "dns",
    "fs",
    "net",
    "os",
    "readline",
    "repl",
    "tls",
    "tty",
    "v8",
    "worker_threads",
];

pub fn find_forbidden_imports(
    source: &str,
    language: SourceLanguage,
) -> Result<Vec<KernelViolation>, RuleError> {
    let tree = parse_source(source, language)?;
    find_forbidden_imports_in_tree(source, language, &tree, DEFAULT_FORBIDDEN_MODULES)
}

pub fn find_forbidden_imports_in_tree(
    source: &str,
    language: SourceLanguage,
    tree: &Tree,
    forbidden_modules: &[&str],
) -> Result<Vec<KernelViolation>, RuleError> {
    let query = Query::new(language.tree_sitter_language(), IMPORT_QUERY)
        .map_err(|err| RuleError::Query(err.to_string()))?;

    let mut cursor = QueryCursor::new();
    let root = tree.root_node();
    let matches = cursor.matches(&query, root, source.as_bytes());

    let capture_names = query.capture_names();
    let mut violations = Vec::new();
    let mut seen = HashSet::new();

    for query_match in matches {
        let mut module_text: Option<String> = None;
        let mut module_node = None;
        let mut callee_text: Option<String> = None;

        for capture in query_match.captures {
            let capture_name = &capture_names[capture.index as usize];
            let text = capture
                .node
                .utf8_text(source.as_bytes())
                .map_err(|err| RuleError::Query(err.to_string()))?;

            match capture_name.as_str() {
                "module" => {
                    module_text = Some(unquote_module(text));
                    module_node = Some(capture.node);
                }
                "callee" => {
                    callee_text = Some(text.to_string());
                }
                _ => {}
            }
        }

        let Some(module_text) = module_text else {
            continue;
        };

        let Some(module_node) = module_node else {
            continue;
        };

        let is_static_import = callee_text.is_none();
        let is_require_call = callee_text.as_deref() == Some("require");

        if !is_static_import && !is_require_call {
            continue;
        }

        if !is_forbidden_module(&module_text, forbidden_modules) {
            continue;
        }

        let position = module_node.start_position();
        let dedupe_key = (module_node.start_byte(), module_node.end_byte());

        if !seen.insert(dedupe_key) {
            continue;
        }

        violations.push(KernelViolation {
            rule_id: "watchllm-rule-imports".to_string(),
            message: format!("Forbidden import detected: {}", module_text),
            location: Location {
                line: position.row + 1,
                column: position.column + 1,
                end_line: None,
                end_column: None,
            },
            severity: "HIGH".to_string(),
            evidence: module_text.clone(),
        });
    }

    Ok(violations)
}

fn unquote_module(raw: &str) -> String {
    let trimmed = raw.trim();

    if trimmed.len() >= 2 {
        let first = trimmed.as_bytes()[0] as char;
        let last = trimmed.as_bytes()[trimmed.len() - 1] as char;

        if matches!(first, '"' | '\'') && first == last {
            return trimmed[1..trimmed.len() - 1].to_string();
        }
    }

    trimmed.to_string()
}

fn is_forbidden_module(module: &str, forbidden_modules: &[&str]) -> bool {
    let normalised = module.strip_prefix("node:").unwrap_or(module);

    forbidden_modules.iter().any(|forbidden| {
        normalised == *forbidden || normalised.starts_with(&format!("{}/", forbidden))
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_forbidden_static_import_in_typescript() {
        let source = r#"
            import childProcess from "child_process";
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-imports");
        assert_eq!(
            violations[0].message,
            "Forbidden import detected: child_process"
        );
        assert_eq!(violations[0].severity, "HIGH");
    }

    #[test]
    fn detects_forbidden_require_in_javascript() {
        let source = r#"
            const childProcess = require("child_process");
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::JavaScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-imports");
        assert_eq!(
            violations[0].message,
            "Forbidden import detected: child_process"
        );
    }

    #[test]
    fn detects_node_prefixed_forbidden_import() {
        let source = r#"
            import vm from "node:vm";
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-imports");
        assert_eq!(violations[0].message, "Forbidden import detected: node:vm");
    }

    #[test]
    fn detects_forbidden_subpath_import() {
        let source = r#"
            import { runInNewContext } from "vm/something";
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-imports");
    }

    #[test]
    fn ignores_allowed_imports() {
        let source = r#"
            import express from "express";
            import fs from "fs";
            const zod = require("zod");
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::TypeScript).unwrap();

        assert!(violations.is_empty());
    }

    #[test]
    fn custom_forbidden_module_list_is_supported() {
        let source = r#"
            import express from "express";
        "#;

        let tree = parse_source(source, SourceLanguage::TypeScript).unwrap();

        let violations =
            find_forbidden_imports_in_tree(source, SourceLanguage::TypeScript, &tree, &["express"])
                .unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].message, "Forbidden import detected: express");
    }
}
