use std::collections::HashSet;

use tree_sitter::{Node, Query, QueryCursor, Tree};

use crate::models::KernelViolation;
use crate::parser::{parse_source, SourceLanguage};

use super::RuleError;

const IMPORT_QUERY: &str = r#"
(import_statement
  source: (string) @module)

(call_expression
  function: (identifier) @callee
  arguments: (arguments (string) @module))
"#;

/// Default forbidden modules — intentionally conservative.
///
/// Only modules that enable *arbitrary code execution* or *sandbox escape*
/// are blocked by default. This matches the Python kernel's
/// ``DEFAULT_FORBIDDEN_MODULES`` in ``forbidden_imports.py``.
///
/// Common Node.js modules (``fs``, ``http``, ``os``, etc.) are available
/// for users to add to a custom list.
pub const DEFAULT_FORBIDDEN_MODULES: &[&str] = &[
    "child_process",
    "vm",
];

/// Elevated-risk modules for deployments that want stricter enforcement.
/// Merge this set into ``forbidden_modules`` for production hardening.
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
    if language == SourceLanguage::Python {
        let tree = parse_source(source, language)?;
        return find_forbidden_python_imports_in_tree(source, &tree, DEFAULT_FORBIDDEN_MODULES);
    }
    let tree = parse_source(source, language)?;
    find_forbidden_imports_in_tree(source, language, &tree, DEFAULT_FORBIDDEN_MODULES)
}

fn walk_python_imports(node: Node, source: &str, paths: &mut Vec<String>) {
    match node.kind() {
        "import_statement" => {
            for i in 0..node.child_count() {
                if let Some(child) = node.child(i) {
                    if child.kind() == "dotted_name" {
                        if let Ok(text) = child.utf8_text(source.as_bytes()) {
                            paths.push(text.trim().to_string());
                        }
                    }
                }
            }
        }
        "import_from_statement" => {
            if let Some(module_node) = node.child_by_field_name("module_name") {
                if let Ok(text) = module_node.utf8_text(source.as_bytes()) {
                    paths.push(text.trim().to_string());
                }
            }
        }
        "call" => {
            if let Some(func_node) = node.child_by_field_name("function") {
                if let Ok(text) = func_node.utf8_text(source.as_bytes()) {
                    if text.trim() == "__import__" {
                        if let Some(args) = node.child_by_field_name("arguments") {
                            for i in 0..args.child_count() {
                                if let Some(child) = args.child(i) {
                                    if child.kind() == "string" {
                                        if let Ok(raw) = child.utf8_text(source.as_bytes()) {
                                            let stripped = raw.trim().trim_matches(|c| c == '\'' || c == '"');
                                            paths.push(stripped.to_string());
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
        _ => {}
    }
    for i in 0..node.child_count() {
        if let Some(child) = node.child(i) {
            walk_python_imports(child, source, paths);
        }
    }
}

fn extract_python_imports(root: Node, source: &str) -> Vec<String> {
    let mut paths = Vec::new();
    walk_python_imports(root, source, &mut paths);
    paths
}

fn find_forbidden_python_imports_in_tree(
    source: &str,
    tree: &Tree,
    forbidden_modules: &[&str],
) -> Result<Vec<KernelViolation>, RuleError> {
    let root = tree.root_node();
    let import_paths = extract_python_imports(root, source);
    let mut violations = Vec::new();
    let mut seen = HashSet::new();

    for path in import_paths {
        if seen.insert(path.clone()) {
            let normalised = path.strip_prefix("node:").unwrap_or(&path);
            if forbidden_modules.iter().any(|m| normalised == *m || normalised.starts_with(&format!("{}/", m))) {
                violations.push(KernelViolation {
                    message: format!("Forbidden import detected: {}", path),
                    rule: "imports".to_string(),
                    line: 0,
                    column: 0,
                    severity: "error".to_string(),
                });
            }
        }
    }

    Ok(violations)
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
            message: format!("Forbidden import detected: {}", module_text),
            rule: "imports".to_string(),
            line: position.row + 1,
            column: position.column + 1,
            severity: "error".to_string(),
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
        assert_eq!(violations[0].rule, "imports");
        assert_eq!(violations[0].message, "Forbidden import detected: child_process");
        assert_eq!(violations[0].severity, "error");
    }

    #[test]
    fn detects_forbidden_require_in_javascript() {
        let source = r#"
            const childProcess = require("child_process");
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::JavaScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule, "imports");
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
        assert_eq!(violations[0].rule, "imports");
        assert_eq!(violations[0].message, "Forbidden import detected: node:vm");
    }

    #[test]
    fn detects_forbidden_subpath_import() {
        let source = r#"
            import { runInNewContext } from "vm/something";
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule, "imports");
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

        let violations = find_forbidden_imports_in_tree(
            source,
            SourceLanguage::TypeScript,
            &tree,
            &["express"],
        )
        .unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].message, "Forbidden import detected: express");
    }

    // --- Python imports ---

    #[test]
    fn python_detects_forbidden_bare_import() {
        let source = r#"
import child_process
import os
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::Python).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule, "imports");
        assert_eq!(violations[0].message, "Forbidden import detected: child_process");
    }

    #[test]
    fn python_detects_forbidden_from_import() {
        let source = r#"
from child_process import exec
from vm import Script
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::Python).unwrap();

        assert_eq!(violations.len(), 2);
    }

    #[test]
    fn python_detects_forbidden_import_call() {
        let source = r#"
module = __import__('child_process')
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::Python).unwrap();

        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn python_ignores_safe_imports() {
        let source = r#"
import os
import sys
from datetime import datetime
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::Python).unwrap();

        assert!(violations.is_empty());
    }

    #[test]
    fn python_recognizes_python_language_variant() {
        let source = r#"
import child_process
        "#;

        let violations = find_forbidden_imports(source, SourceLanguage::Python).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule, "imports");
    }
}
