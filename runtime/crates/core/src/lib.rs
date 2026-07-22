// WatchLLM Core Library
// This crate contains all AST evaluation and enforcement rules.
// It is fully agnostic of the host environment (Wasm/CLI).

pub mod engine;
pub mod models;
pub mod parser;
pub mod rules;

pub fn check_sanity() -> bool {
    true
}
