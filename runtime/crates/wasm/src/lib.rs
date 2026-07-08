use std::convert::TryFrom;
use std::panic::{catch_unwind, AssertUnwindSafe};

use serde_json::Value;
use wasm_bindgen::prelude::*;

use watchllm_core::engine;
use watchllm_core::models::KernelExecutionResult;
use watchllm_core::parser::SourceLanguage;

#[wasm_bindgen]
pub fn evaluate_source(source: &str, config_json: &str) -> String {
    match catch_unwind(AssertUnwindSafe(|| evaluate_source_inner(source, config_json, None))) {
        Ok(json) => json,
        Err(_) => serialize_result(error_result(
            "Runtime panic caught before crossing Wasm boundary".to_string(),
        )),
    }
}

/// Evaluate source with an agent role claim (connects Phase 1 token flow → Phase 4 Wasm).
///
/// `role_json` is a JSON string such as `"read-only-agent"` or `null`.
/// When a known restrictive role is provided, certain rules are skipped to
/// match the Python kernel's role-filtered rule set.
#[wasm_bindgen]
pub fn evaluate_source_with_role(source: &str, config_json: &str, role_json: &str) -> String {
    let role: Option<String> = serde_json::from_str(role_json).unwrap_or(None);
    match catch_unwind(AssertUnwindSafe(|| evaluate_source_inner(source, config_json, role.as_deref()))) {
        Ok(json) => json,
        Err(_) => serialize_result(error_result(
            "Runtime panic caught before crossing Wasm boundary".to_string(),
        )),
    }
}

fn evaluate_source_inner(source: &str, config_json: &str, _role: Option<&str>) -> String {
    let language = match language_from_config(config_json) {
        Ok(language) => language,
        Err(message) => return serialize_result(error_result(message)),
    };

    // Role-based rule filtering will be threaded through the core engine
    // in a follow-up; for now all roles use the full rule set.
    let result = engine::evaluate_source(source, language);
    serialize_result(result)
}

fn language_from_config(config_json: &str) -> Result<SourceLanguage, String> {
    let trimmed = config_json.trim();

    if trimmed.is_empty() {
        return Ok(SourceLanguage::TypeScript);
    }

    let value: Value =
        serde_json::from_str(trimmed).map_err(|err| format!("Config JSON parse error: {}", err))?;

    let language = value
        .get("language")
        .or_else(|| value.get("sourceLanguage"))
        .and_then(Value::as_str)
        .unwrap_or("typescript");

    SourceLanguage::try_from(language).map_err(|err| format!("Parser error: {:?}", err))
}

fn serialize_result(result: KernelExecutionResult) -> String {
    match serde_json::to_string(&result) {
        Ok(json) => json,
        Err(err) => fallback_error_json(&format!("Result serialization error: {}", err)),
    }
}

fn error_result(message: String) -> KernelExecutionResult {
    KernelExecutionResult {
        status: "error".to_string(),
        exit_code: 2,
        payload: None,
        error: Some(message),
    }
}

fn fallback_error_json(message: &str) -> String {
    let escaped_message = message.replace('\\', "\\\\").replace('"', "\\\"");

    format!(
        r#"{{"status":"error","exit_code":2,"payload":null,"error":"{}"}}"#,
        escaped_message
    )
}
