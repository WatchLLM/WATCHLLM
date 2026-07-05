pub mod auth_flow;
pub mod boundaries;
pub mod imports;
pub mod secrets;

use crate::parser::ParseError;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RuleError {
    Parse(ParseError),
    Query(String),
}

impl From<ParseError> for RuleError {
    fn from(value: ParseError) -> Self {
        Self::Parse(value)
    }
}
