use std::collections::HashMap;

use crate::models::{KernelViolation, Location};
use crate::parser::{parse_source, SourceLanguage};
use crate::rules::RuleError;
use tree_sitter::Node;

type ModuleBoundary = Vec<(String, String)>;

fn default_boundary_map() -> HashMap<String, ModuleBoundary> {
    let mut m = HashMap::new();
    m.insert(
        "auth".to_string(),
        vec![("db".to_string(), "internal".to_string())],
    );
    m
}

pub fn check_boundaries(
    source: &str,
    language: SourceLanguage,
) -> Result<Vec<KernelViolation>, RuleError> {
    let tree = parse_source(source, language)?;
    let root = tree.root_node();

    let is_boundary_layer = source.contains("// @boundary-layer");
    let boundary_map = default_boundary_map();

    let import_nodes = find_import_nodes(root);
    let mut violations = Vec::new();

    for node in import_nodes {
        let Some(module_specifier) = extract_module_specifier(node, source) else {
            continue;
        };

        let position = node.start_position();

        let mut flagged = false;
        if let Some((target_module, target_surface)) = classify_import_target(&module_specifier) {
            if !is_boundary_layer {
                for (src_mod, rules) in &boundary_map {
                    if rules.contains(&(target_module.clone(), target_surface.clone())) {
                        violations.push(KernelViolation {
                            rule_id: "watchllm-rule-boundaries".to_string(),
                            message: format!(
                                "Boundary violation: {} cannot import {}/{}",
                                src_mod, target_module, target_surface
                            ),
                            location: Location {
                                line: position.row + 1,
                                column: position.column + 1,
                                end_line: None,
                                end_column: None,
                            },
                            severity: "HIGH".to_string(),
                            evidence: module_specifier.clone(),
                        });
                        flagged = true;
                        break;
                    }
                }
            }
        }

        if !flagged && module_specifier.starts_with("@internal/") && !is_boundary_layer {
            violations.push(KernelViolation {
                rule_id: "watchllm-rule-boundaries".to_string(),
                message: format!(
                    "Boundary import '{}' is only allowed in boundary-layer files",
                    module_specifier
                ),
                location: Location {
                    line: position.row + 1,
                    column: position.column + 1,
                    end_line: None,
                    end_column: None,
                },
                severity: "HIGH".to_string(),
                evidence: module_specifier.clone(),
            });
        }
    }

    Ok(violations)
}

fn classify_import_target(path: &str) -> Option<(String, String)> {
    let normalised = path.trim_matches(|c| c == '\'' || c == '"' || c == '`');

    if normalised == "@internal/db" || normalised.starts_with("@internal/db/") {
        return Some(("db".to_string(), "internal".to_string()));
    }

    if normalised == "@app/db/internal" || normalised.starts_with("@app/db/internal/") {
        return Some(("db".to_string(), "internal".to_string()));
    }
    if normalised == "@app/db/public" || normalised.starts_with("@app/db/public/") {
        return Some(("db".to_string(), "public".to_string()));
    }

    for relative_prefix in &[
        "./db/internal",
        "../db/internal",
        "../../db/internal",
        "../../../db/internal",
    ] {
        if normalised == *relative_prefix
            || normalised.starts_with(&format!("{}/", relative_prefix))
        {
            return Some(("db".to_string(), "internal".to_string()));
        }
    }
    for relative_prefix in &[
        "./db/public",
        "../db/public",
        "../../db/public",
        "../../../db/public",
    ] {
        if normalised == *relative_prefix
            || normalised.starts_with(&format!("{}/", relative_prefix))
        {
            return Some(("db".to_string(), "public".to_string()));
        }
    }

    None
}

fn find_import_nodes(node: Node) -> Vec<Node> {
    let mut results = Vec::new();
    if node.kind() == "import_statement" {
        results.push(node);
    }
    for i in 0..node.child_count() {
        if let Some(child) = node.child(i) {
            results.extend(find_import_nodes(child));
        }
    }
    results
}

fn extract_module_specifier(node: Node, source: &str) -> Option<String> {
    for i in 0..node.child_count() {
        let child = node.child(i)?;
        if child.kind() == "string" {
            let raw = child.utf8_text(source.as_bytes()).ok()?;
            let trimmed = raw.trim_matches(|c| c == '\'' || c == '"' || c == '`');
            return Some(trimmed.to_string());
        }
    }
    None
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allows_boundary_import_in_boundary_layer_file() {
        let source = r#"
            // @boundary-layer
            import { connect } from "@internal/db";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn flags_boundary_import_in_non_boundary_file() {
        let source = r#"
            import { connect } from "@internal/db";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert_eq!(violations.len(), 1);
        let v = &violations[0];
        assert_eq!(v.rule_id, "watchllm-rule-boundaries");
        assert_eq!(v.severity, "HIGH");
    }

    #[test]
    fn ignores_non_boundary_imports() {
        let source = r#"
            import { readFile } from "fs";
            import express from "express";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn handles_multiple_boundary_imports() {
        let source = r#"
            import { connect } from "@internal/db";
            import { authenticate } from "@internal/auth";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.len() >= 2);
    }

    #[test]
    fn boundary_marker_comment_is_case_sensitive() {
        let source = r#"
            // @Boundary-Layer
            import { connect } from "@internal/db";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(!violations.is_empty());
    }

    #[test]
    fn flags_db_internal_import_from_non_boundary() {
        let source = r#"
            import { query } from "@app/db/internal";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(
            !violations.is_empty(),
            "@app/db/internal should be a boundary violation"
        );
    }

    #[test]
    fn allows_db_public_import_even_from_non_boundary() {
        let source = r#"
            import { query } from "@app/db/public";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(
            violations.is_empty(),
            "@app/db/public should not be a boundary violation"
        );
    }

    #[test]
    fn relative_db_internal_is_flagged() {
        let source = r#"
            import { query } from "../db/internal";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(
            !violations.is_empty(),
            "../db/internal should be a boundary violation"
        );
    }

    #[test]
    fn internal_db_slash_subpath_is_flagged() {
        let source = r#"
            import { connect } from "@internal/db/connection";
        "#;
        let violations = check_boundaries(source, SourceLanguage::TypeScript).unwrap();
        assert!(!violations.is_empty());
    }
}
