use std::convert::TryFrom;
use tree_sitter::{Language, Parser as TreeSitterParser, Tree};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum SourceLanguage {
    JavaScript,
    TypeScript,
    Tsx,
}

impl SourceLanguage {
    pub(crate) fn tree_sitter_language(self) -> Language {
        match self {
            SourceLanguage::JavaScript => tree_sitter_javascript::language(),
            SourceLanguage::TypeScript => tree_sitter_typescript::language_typescript(),
            SourceLanguage::Tsx => tree_sitter_typescript::language_tsx(),
        }
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ParseError {
    UnsupportedLanguage(String),
    LanguageLoad(String),
    ParseFailed,
    SyntaxError,
}

impl TryFrom<&str> for SourceLanguage {
    type Error = ParseError;

    fn try_from(value: &str) -> Result<Self, Self::Error> {
        match value.to_ascii_lowercase().as_str() {
            "javascript" | "js" => Ok(SourceLanguage::JavaScript),
            "typescript" | "ts" => Ok(SourceLanguage::TypeScript),
            "tsx" => Ok(SourceLanguage::Tsx),
            other => Err(ParseError::UnsupportedLanguage(other.to_string())),
        }
    }
}

pub fn parse_source(source: &str, language: SourceLanguage) -> Result<Tree, ParseError> {
    let mut parser = TreeSitterParser::new();
    let ts_language = language.tree_sitter_language();

    parser
        .set_language(ts_language)
        .map_err(|err| ParseError::LanguageLoad(err.to_string()))?;

    let tree = parser.parse(source, None).ok_or(ParseError::ParseFailed)?;

    if tree.root_node().has_error() {
        return Err(ParseError::SyntaxError);
    }

    Ok(tree)
}

pub fn parse_source_with_language_name(source: &str, language: &str) -> Result<Tree, ParseError> {
    let parsed_language = SourceLanguage::try_from(language)?;
    parse_source(source, parsed_language)
}

#[cfg(test)]
mod tests {
    use super::*;
    use tree_sitter::Node;

    fn contains_kind(node: Node, kind: &str) -> bool {
        if node.kind() == kind {
            return true;
        }

        for index in 0..node.child_count() {
            if let Some(child) = node.child(index) {
                if contains_kind(child, kind) {
                    return true;
                }
            }
        }

        false
    }

    fn contains_identifier_named(node: Node, source: &str, expected: &str) -> bool {
        if node.kind() == "identifier" {
            if let Ok(text) = node.utf8_text(source.as_bytes()) {
                if text == expected {
                    return true;
                }
            }
        }

        for index in 0..node.child_count() {
            if let Some(child) = node.child(index) {
                if contains_identifier_named(child, source, expected) {
                    return true;
                }
            }
        }

        false
    }

    #[test]
    fn parses_dummy_typescript_and_finds_specific_nodes() {
        let source = r#"
            const answer: number = 42;

            function greet(name: string): string {
                return `hello ${name}`;
            }
        "#;

        let tree = parse_source(source, SourceLanguage::TypeScript).unwrap();
        let root = tree.root_node();

        assert_eq!(root.kind(), "program");
        assert!(!root.has_error());
        assert!(contains_kind(root, "lexical_declaration"));
        assert!(contains_kind(root, "function_declaration"));
        assert!(contains_kind(root, "type_annotation"));
        assert!(contains_identifier_named(root, source, "answer"));
        assert!(contains_identifier_named(root, source, "greet"));
    }

    #[test]
    fn parses_javascript() {
        let source = r#"
            const value = require("fs");
        "#;

        let tree = parse_source(source, SourceLanguage::JavaScript).unwrap();
        let root = tree.root_node();

        assert_eq!(root.kind(), "program");
        assert!(!root.has_error());
        assert!(contains_kind(root, "lexical_declaration"));
        assert!(contains_kind(root, "call_expression"));
    }

    #[test]
    fn rejects_unsupported_language_name() {
        let result = parse_source_with_language_name("const x = 1;", "python");

        assert_eq!(
            result.unwrap_err(),
            ParseError::UnsupportedLanguage("python".to_string())
        );
    }

    #[test]
    fn detects_typescript_syntax_errors() {
        let result = parse_source("const =", SourceLanguage::TypeScript);

        assert_eq!(result.unwrap_err(), ParseError::SyntaxError);
    }
}
