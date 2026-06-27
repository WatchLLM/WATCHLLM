use std::panic::{catch_unwind, AssertUnwindSafe};

use wasm_bindgen::prelude::*;

use watchllm_core::engine;
use watchllm_core::models::KernelExecutionResult;

#[wasm_bindgen]
pub fn evaluate_source(source: &str, filepath: &str, language: &str, mode: &str) -> String {
    match catch_unwind(AssertUnwindSafe(|| {
        evaluate_source_inner(source, filepath, language, mode)
    })) {
        Ok(json) => json,
        Err(_) => serialize_result(error_result(
            "Runtime panic caught before crossing Wasm boundary".to_string(),
        )),
    }
}

fn evaluate_source_inner(source: &str, filepath: &str, language: &str, mode: &str) -> String {
    let fp = if filepath.is_empty() {
        None
    } else {
        Some(filepath)
    };

    let result = engine::evaluate_source_with_language_name(source, language, fp, mode);
    serialize_result(result)
}

fn serialize_result(result: KernelExecutionResult) -> String {
    match serde_json::to_string(&result) {
        Ok(json) => json,
        Err(err) => fallback_error_json(&format!("Result serialization error: {}", err)),
    }
}

fn error_result(message: String) -> KernelExecutionResult {
    KernelExecutionResult {
        decision: "ALLOW".to_string(),
        mode: "enforce".to_string(),
        file_path: None,
        language: "javascript".to_string(),
        rule_results: vec![],
        error: Some(message),
    }
}

fn fallback_error_json(message: &str) -> String {
    let escaped_message = message.replace('\\', "\\\\").replace('"', "\\\"");
    format!(
        r#"{{"decision":"ALLOW","mode":"enforce","language":"javascript","rule_results":[],"error":"{}"}}"#,
        escaped_message
    )
}
