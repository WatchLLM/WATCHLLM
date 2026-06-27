use std::collections::HashSet;

use regex::Regex;
use tree_sitter::{Query, QueryCursor, Tree};

use crate::models::{KernelViolation, Location};
use crate::parser::{parse_source, SourceLanguage};

use super::RuleError;

// ---------------------------------------------------------------------------
// Tree-sitter query
// ---------------------------------------------------------------------------

const SECRET_QUERY: &str = r#"
(variable_declarator
  name: (identifier) @secret.name
  value: [(string) (template_string)] @secret.value)

(assignment_expression
  left: (identifier) @secret.name
  right: [(string) (template_string)] @secret.value)

(assignment_expression
  left: (member_expression
    property: (property_identifier) @secret.name)
  right: [(string) (template_string)] @secret.value)

(pair
  key: [(property_identifier) (string)] @secret.name
  value: [(string) (template_string)] @secret.value)
"#;

// ---------------------------------------------------------------------------
// Name-based markers
// ---------------------------------------------------------------------------

const SECRET_NAME_MARKERS: &[&str] = &[
    "api_key",
    "apikey",
    "access_key",
    "accesskey",
    "secret",
    "client_secret",
    "clientsecret",
    "token",
    "auth_token",
    "authtoken",
    "password",
    "passwd",
    "pwd",
    "private_key",
    "privatekey",
];

// ---------------------------------------------------------------------------
// Value-based patterns
// ---------------------------------------------------------------------------

fn build_secret_patterns() -> Vec<Regex> {
    vec![
        Regex::new(r"sk_live_[0-9a-zA-Z]{10,}").expect("invalid regex"),
        Regex::new(r"pk_live_[0-9a-zA-Z]{10,}").expect("invalid regex"),
        Regex::new(r"rk_live_[0-9a-zA-Z]{10,}").expect("invalid regex"),
        Regex::new(r"whsec_[0-9a-zA-Z]{10,}").expect("invalid regex"),
        Regex::new(r"sk_test_[0-9a-zA-Z]{10,}").expect("invalid regex"),
        Regex::new(r"pk_test_[0-9a-zA-Z]{10,}").expect("invalid regex"),
        Regex::new(r"rk_test_[0-9a-zA-Z]{10,}").expect("invalid regex"),
        Regex::new(r"sk-").expect("invalid regex"),
        Regex::new(r"xox[baprs]-[0-9a-zA-Z-]{10,}").expect("invalid regex"),
        Regex::new(r"ghp_[0-9a-zA-Z]{36}").expect("invalid regex"),
        Regex::new(r"gho_[0-9a-zA-Z]{36}").expect("invalid regex"),
        Regex::new(r"ghu_[0-9a-zA-Z]{36}").expect("invalid regex"),
        Regex::new(r"ghs_[0-9a-zA-Z]{36}").expect("invalid regex"),
        Regex::new(r"ghr_[0-9a-zA-Z]{36}").expect("invalid regex"),
        Regex::new(r"AKIA[0-9A-Z]{16}").expect("invalid regex"),
        Regex::new(r"ASIA[0-9A-Z]{16}").expect("invalid regex"),
        Regex::new(r"AIza[0-9A-Za-z\-_]{35}").expect("invalid regex"),
        Regex::new(r"ya29\.[0-9A-Za-z\-_]+").expect("invalid regex"),
        Regex::new(r"sk-ant-api03-[0-9a-zA-Z\-_]{20,}").expect("invalid regex"),
        Regex::new(r"sk-or-v1-[0-9a-f]{64}").expect("invalid regex"),
        Regex::new(r"sk-proj-[0-9a-zA-Z\-_]{20,}").expect("invalid regex"),
        Regex::new(r"sk-svcacct-[0-9a-zA-Z\-_]{20,}").expect("invalid regex"),
        Regex::new(r"sk-[0-9a-zA-Z]{48}").expect("invalid regex"),
        Regex::new(r"sk-[0-9a-zA-Z]{32}").expect("invalid regex"),
        Regex::new(r"sk-[0-9a-zA-Z]{20,}").expect("invalid regex"),
    ]
}

fn build_safe_patterns() -> Vec<Regex> {
    vec![
        Regex::new(r"process\.env\.").expect("invalid regex"),
        Regex::new(r"os\.getenv\(").expect("invalid regex"),
        Regex::new(r"os\.environ\[").expect("invalid regex"),
        Regex::new(r"getenv\(").expect("invalid regex"),
        Regex::new(r"env\(").expect("invalid regex"),
        Regex::new(r"config\(").expect("invalid regex"),
        Regex::new(r"secret\(").expect("invalid regex"),
        Regex::new(r"vault\(").expect("invalid regex"),
        Regex::new(r"credential\(").expect("invalid regex"),
        Regex::new(r"key\(").expect("invalid regex"),
        Regex::new(r"token\(").expect("invalid regex"),
    ]
}

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

pub fn find_secret_literals(
    source: &str,
    language: SourceLanguage,
) -> Result<Vec<KernelViolation>, RuleError> {
    let tree = parse_source(source, language)?;
    find_secret_literals_in_tree(source, language, &tree)
}

pub fn find_secret_literals_in_tree(
    source: &str,
    _language: SourceLanguage,
    tree: &Tree,
) -> Result<Vec<KernelViolation>, RuleError> {
    let query = Query::new(tree_sitter_typescript::language_typescript(), SECRET_QUERY)
        .map_err(|err| RuleError::Query(err.to_string()))?;

    let secret_patterns = build_secret_patterns();
    let safe_patterns = build_safe_patterns();

    let mut cursor = QueryCursor::new();
    let root = tree.root_node();
    let matches = cursor.matches(&query, root, source.as_bytes());

    let capture_names = query.capture_names();
    let mut violations = Vec::new();
    let mut seen = HashSet::new();

    for query_match in matches {
        let mut name_text: Option<String> = None;
        let mut value_text: Option<String> = None;
        let mut value_node = None;

        for capture in query_match.captures {
            let capture_name = &capture_names[capture.index as usize];

            let text = capture
                .node
                .utf8_text(source.as_bytes())
                .map_err(|err| RuleError::Query(err.to_string()))?;

            match capture_name.as_str() {
                "secret.name" => {
                    name_text = Some(normalise_identifier(text));
                }
                "secret.value" => {
                    value_text = Some(text.to_string());
                    value_node = Some(capture.node);
                }
                _ => {}
            }
        }

        let Some(name_text) = name_text else {
            continue;
        };

        let Some(value_text) = value_text else {
            continue;
        };

        let Some(value_node) = value_node else {
            continue;
        };

        let unquoted = unquote(&value_text);

        if unquoted.trim().is_empty() {
            continue;
        }

        if is_safe_retrieval(source, &unquoted, &safe_patterns) {
            continue;
        }

        if !is_secret_name(&name_text) && !matches_secret_pattern(&unquoted, &secret_patterns) {
            continue;
        }

        let position = value_node.start_position();
        let dedupe_key = (value_node.start_byte(), value_node.end_byte());

        if !seen.insert(dedupe_key) {
            continue;
        }

        violations.push(KernelViolation {
            rule_id: "watchllm-rule-secrets".to_string(),
            message: "Secret literal detected".to_string(),
            location: Location {
                line: position.row + 1,
                column: position.column + 1,
                end_line: None,
                end_column: None,
            },
            severity: "HIGH".to_string(),
            evidence: unquoted.chars().take(80).collect(),
        });
    }

    Ok(violations)
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn normalise_identifier(raw: &str) -> String {
    unquote(raw).to_ascii_lowercase().replace('-', "_")
}

fn is_secret_name(name: &str) -> bool {
    SECRET_NAME_MARKERS
        .iter()
        .any(|marker| name.contains(marker))
}

fn matches_secret_pattern(value: &str, patterns: &[Regex]) -> bool {
    patterns.iter().any(|pat| pat.is_match(value))
}

fn is_safe_retrieval(full_source: &str, _value: &str, patterns: &[Regex]) -> bool {
    patterns.iter().any(|pat| pat.is_match(full_source))
}

fn unquote(raw: &str) -> String {
    let trimmed = raw.trim();

    if trimmed.len() >= 2 {
        let first = trimmed.as_bytes()[0] as char;
        let last = trimmed.as_bytes()[trimmed.len() - 1] as char;

        if matches!(first, '"' | '\'' | '`') && first == last {
            return trimmed[1..trimmed.len() - 1].to_string();
        }
    }

    trimmed.to_string()
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn detects_secret_literal_in_typescript_variable() {
        let source = r#"
            const apiKey = "sk_live_123";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
        assert_eq!(violations[0].message, "Secret literal detected");
        assert_eq!(violations[0].severity, "HIGH");
    }

    #[test]
    fn detects_secret_literal_in_object_property() {
        let source = r#"
            const config = {
                password: "super-secret"
            };
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn detects_secret_literal_assignment_expression() {
        let source = r#"
            settings.token = "some-secret-value";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert!(!violations.is_empty(), "member expression with secret-like property name should trigger");
    }

    #[test]
    fn detects_private_key_style_secret_name() {
        let source = r#"
            const privateKey = "abc123";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn ignores_non_secret_string_literal() {
        let source = r#"
            const message = "hello world";
            const label = "secret text in harmless value";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert!(violations.is_empty());
    }

    #[test]
    fn ignores_empty_secret_literal() {
        let source = r#"
            const apiKey = "";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert!(violations.is_empty());
    }

    #[test]
    fn detects_secret_by_value_pattern_stripe_live() {
        let source = r#"
            const x = "sk_live_abc123def456";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn detects_secret_by_value_pattern_github_pat() {
        let source = r#"
            const x = "ghp_1234567890abcdef1234567890abcdef1234";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn detects_secret_by_value_pattern_aws_key_with_secretlike_name() {
        let source = r#"
            const apiKey = "AKIA1234567890ABCD";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn detects_secret_by_value_pattern_slack_token() {
        let source = r#"
            const x = "xoxb-1234567890-abcdefghijklm";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn detects_secret_by_value_pattern_gcp_key() {
        let source = r#"
            const x = "AIzaSyD1234567890abcdefghijklmnopqrstuv";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn detects_secret_by_value_in_member_expression() {
        let source = r#"
            settings.token = "abc123";
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "watchllm-rule-secrets");
    }

    #[test]
    fn safe_retrieval_process_env_is_allowed() {
        let source = r#"
            const apiKey = process.env.API_KEY || "fallback";
            const token = os.getenv("AUTH_TOKEN");
            const secret = vault("my-secret");
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert!(violations.is_empty());
    }

    #[test]
    fn safe_retrieval_config_call_is_allowed() {
        let source = r#"
            const password = config("db.password");
        "#;

        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert!(violations.is_empty());
    }

    #[test]
    fn violation_has_location_info() {
        let source = "const apiKey = \"sk_live_xxx\";\n";
        let violations = find_secret_literals(source, SourceLanguage::TypeScript).unwrap();

        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].location.line, 1);
        assert_eq!(violations[0].location.column, 15);
        assert!(violations[0].location.end_line.is_none());
        assert_eq!(violations[0].evidence, "sk_live_xxx");
    }
}
