// WatchLLM Core Library
// This crate contains all AST evaluation and enforcement rules.
// It is fully agnostic of the host environment (Wasm/CLI).

pub mod models;
pub mod parser;
pub mod rules;
pub mod engine;

pub fn check_sanity() -> bool {
    true
}
