use std::collections::HashSet;

use crate::models::{KernelViolation, Location};
use crate::parser::{parse_source, SourceLanguage};
use crate::rules::RuleError;
use tree_sitter::Node;

pub fn check_auth_flow(
    source: &str,
    language: SourceLanguage,
) -> Result<Vec<KernelViolation>, RuleError> {
    let tree = parse_source(source, language)?;
    let root = tree.root_node();

    let mut violations = Vec::new();
    let mut seen = HashSet::new();
    let block_nodes = find_block_nodes(root);

    for block in block_nodes {
        let mut saw_definite_guard = false;
        let mut saw_ambiguous_guard = false;

        for i in 0..block.named_child_count() {
            let Some(child) = block.named_child(i) else {
                continue;
            };

            if is_branch_node(child) {
                if block_contains_auth_call(child, source) {
                    saw_ambiguous_guard = true;
                }
                continue;
            }

            let Some(call_node) = find_top_level_call(child) else {
                continue;
            };

            let callee = callee_text(call_node, source);

            if is_auth_call(&callee) {
                saw_definite_guard = true;
                continue;
            }

            if is_db_call(&callee) {
                if saw_definite_guard {
                    continue;
                }

                if saw_ambiguous_guard {
                    continue;
                }

                let dedupe_key = (call_node.id(), call_node.start_byte());
                if seen.insert(dedupe_key) {
                    let pos = call_node.start_position();
                    violations.push(KernelViolation {
                        rule_id: "watchllm-rule-auth".to_string(),
                        message: "Database call before authentication check".to_string(),
                        location: Location {
                            line: pos.row + 1,
                            column: pos.column + 1,
                            end_line: None,
                            end_column: None,
                        },
                        severity: "HIGH".to_string(),
                        evidence: callee,
                    });
                }
                break;
            }
        }
    }

    Ok(violations)
}

fn is_branch_node(node: Node) -> bool {
    let branch_kinds = [
        "if_statement",
        "else_clause",
        "switch_case",
        "while_statement",
        "for_statement",
        "try_statement",
        "catch_clause",
    ];
    branch_kinds.contains(&node.kind())
}

fn block_contains_auth_call(node: Node, source: &str) -> bool {
    if node.kind() == "call_expression" {
        return is_auth_call(&callee_text(node, source));
    }

    for i in 0..node.child_count() {
        if let Some(child) = node.child(i) {
            if block_contains_auth_call(child, source) {
                return true;
            }
        }
    }

    false
}

fn find_block_nodes(node: Node) -> Vec<Node> {
    let mut results = Vec::new();
    let block_kinds = [
        "function_declaration",
        "method_definition",
        "arrow_function",
        "if_statement",
        "while_statement",
        "for_statement",
        "try_statement",
        "catch_clause",
        "block",
        "statement_block",
        "program",
    ];

    if block_kinds.contains(&node.kind()) {
        results.push(node);
    }

    for i in 0..node.child_count() {
        if let Some(child) = node.child(i) {
            results.extend(find_block_nodes(child));
        }
    }

    results
}

fn find_top_level_call(node: Node) -> Option<Node> {
    let stop_kinds = [
        "function_declaration",
        "method_definition",
        "arrow_function",
        "if_statement",
        "else_clause",
        "switch_case",
        "while_statement",
        "for_statement",
        "try_statement",
        "catch_clause",
        "block",
        "statement_block",
    ];

    find_call_with_boundary(node, &stop_kinds)
}

fn find_call_with_boundary<'a>(node: Node<'a>, stop_kinds: &[&str]) -> Option<Node<'a>> {
    if node.kind() == "call_expression" {
        return Some(node);
    }

    if stop_kinds.contains(&node.kind()) {
        return None;
    }

    for i in 0..node.child_count() {
        if let Some(child) = node.child(i) {
            if let Some(found) = find_call_with_boundary(child, stop_kinds) {
                return Some(found);
            }
        }
    }

    None
}

fn callee_text(call_node: Node, source: &str) -> String {
    let function_node = match call_node.child(0) {
        Some(n) => n,
        None => return String::new(),
    };

    if function_node.kind() == "member_expression" {
        return reconstruct_member_expression(function_node, source);
    }

    function_node
        .utf8_text(source.as_bytes())
        .unwrap_or("")
        .to_string()
}

fn reconstruct_member_expression(node: Node, source: &str) -> String {
    let object = node.child(0);
    let property = node.child(2);

    let object_text = match object {
        Some(obj) => {
            if obj.kind() == "member_expression" {
                reconstruct_member_expression(obj, source)
            } else {
                obj.utf8_text(source.as_bytes()).unwrap_or("").to_string()
            }
        }
        None => String::new(),
    };

    let property_text = match property {
        Some(prop) => prop.utf8_text(source.as_bytes()).unwrap_or("").to_string(),
        None => String::new(),
    };

    if object_text.is_empty() {
        property_text
    } else {
        format!("{}.{}", object_text, property_text)
    }
}

fn is_db_call(callee: &str) -> bool {
    let db_patterns = ["db.query", "db.execute", "db.run", "db.get", "db.all"];
    db_patterns.iter().any(|p| *p == callee)
}

fn is_auth_call(callee: &str) -> bool {
    let auth_patterns = [
        "auth.verify",
        "auth.check",
        "auth.authenticate",
        "auth.authorize",
    ];
    auth_patterns.iter().any(|p| *p == callee)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn allows_auth_before_db() {
        let source = r#"
            function handle() {
                auth.verify(token);
                db.query("SELECT * FROM users");
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn flags_db_before_auth() {
        let source = r#"
            function handle() {
                db.query("SELECT * FROM users");
                auth.verify(token);
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert_eq!(violations.len(), 1);
        let v = &violations[0];
        assert_eq!(v.rule_id, "watchllm-rule-auth");
        assert_eq!(v.severity, "HIGH");
    }

    #[test]
    fn flags_db_without_auth() {
        let source = r#"
            function handle() {
                db.query("SELECT * FROM users");
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn ignores_auth_only() {
        let source = r#"
            function handle() {
                auth.verify(token);
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn handles_multiple_blocks() {
        let source = r#"
            function first() {
                db.query("SELECT 1");
            }
            function second() {
                auth.verify(token);
                db.query("SELECT 2");
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn respects_if_block() {
        let source = r#"
            if (condition) {
                db.query("SELECT * FROM users");
                auth.verify(token);
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn handles_arrow_function() {
        let source = r#"
            const handler = () => {
                db.query("SELECT * FROM users");
                auth.verify(token);
            };
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert_eq!(violations.len(), 1);
    }

    #[test]
    fn ambiguous_auth_in_branch_is_inconclusive_not_fail() {
        let source = r#"
            function handle() {
                if (condition) {
                    auth.verify(token);
                }
                db.query("SELECT * FROM users");
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn branch_contained_auth_before_db_is_inconclusive() {
        let source = r#"
            function handle() {
                if (isAdmin) {
                    auth.verify(token);
                }
                db.query("DELETE FROM users");
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn auth_inside_while_branch_is_inconclusive() {
        let source = r#"
            function handle() {
                while (retry) {
                    auth.verify(token);
                }
                db.query("SELECT 1");
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn auth_in_try_block_is_inconclusive() {
        let source = r#"
            function handle() {
                try {
                    auth.verify(token);
                } catch (e) {}
                db.query("SELECT 1");
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert!(violations.is_empty());
    }

    #[test]
    fn db_before_auth_in_same_branch_still_fails() {
        let source = r#"
            function handle() {
                if (condition) {
                    db.query("SELECT * FROM users");
                    auth.verify(token);
                }
            }
        "#;
        let violations = check_auth_flow(source, SourceLanguage::TypeScript).unwrap();
        assert_eq!(violations.len(), 1);
    }
}
