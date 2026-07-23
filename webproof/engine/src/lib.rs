//! Deterministic local commitment engine for WatchLLM WebProof.
//!
//! This crate constructs local SHA-256 Merkle commitments. It does not produce
//! TLS proofs, prove remote data, or attest to any server response.

use std::collections::HashSet;
use std::fmt::Write as _;
use std::sync::{Mutex, MutexGuard};

use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyDict, PyInt, PyList, PyString, PyTuple};
use sha2::{Digest, Sha256};

const LEAF_DOMAIN: &[u8] = b"watchllm-webproof-local-leaf-v1\0";
const NODE_DOMAIN: &[u8] = b"watchllm-webproof-local-node-v1\0";

#[derive(Debug, Clone, PartialEq, Eq)]
enum JsonValue {
    Null,
    Bool(bool),
    Integer(String),
    String(String),
    Array(Vec<JsonValue>),
    Object(Vec<(String, JsonValue)>),
}

fn write_json_string(value: &str, output: &mut String) {
    output.push('"');
    for character in value.chars() {
        match character {
            '"' => output.push_str("\\\""),
            '\\' => output.push_str("\\\\"),
            '\u{08}' => output.push_str("\\b"),
            '\u{0c}' => output.push_str("\\f"),
            '\n' => output.push_str("\\n"),
            '\r' => output.push_str("\\r"),
            '\t' => output.push_str("\\t"),
            character if character <= '\u{1f}' => {
                write!(output, "\\u{:04x}", character as u32)
                    .expect("writing to String cannot fail");
            }
            character if character.is_ascii() => output.push(character),
            character if (character as u32) <= 0xffff => {
                write!(output, "\\u{:04x}", character as u32)
                    .expect("writing to String cannot fail");
            }
            character => {
                let scalar = character as u32 - 0x1_0000;
                let high = 0xd800 + (scalar >> 10);
                let low = 0xdc00 + (scalar & 0x3ff);
                write!(output, "\\u{high:04x}\\u{low:04x}").expect("writing to String cannot fail");
            }
        }
    }
    output.push('"');
}

fn write_canonical(value: &JsonValue, output: &mut String) {
    match value {
        JsonValue::Null => output.push_str("null"),
        JsonValue::Bool(value) => output.push_str(if *value { "true" } else { "false" }),
        JsonValue::Integer(value) => output.push_str(value),
        JsonValue::String(value) => write_json_string(value, output),
        JsonValue::Array(values) => {
            output.push('[');
            for (index, value) in values.iter().enumerate() {
                if index != 0 {
                    output.push(',');
                }
                write_canonical(value, output);
            }
            output.push(']');
        }
        JsonValue::Object(entries) => {
            output.push('{');
            let mut sorted: Vec<_> = entries.iter().collect();
            sorted.sort_by(|left, right| left.0.cmp(&right.0));
            for (index, (key, value)) in sorted.into_iter().enumerate() {
                if index != 0 {
                    output.push(',');
                }
                write_json_string(key, output);
                output.push(':');
                write_canonical(value, output);
            }
            output.push('}');
        }
    }
}

fn canonical_bytes(value: &JsonValue) -> Vec<u8> {
    let mut output = String::new();
    write_canonical(value, &mut output);
    output.into_bytes()
}

fn leaf_hash(canonical: &[u8]) -> [u8; 32] {
    Sha256::new()
        .chain_update(LEAF_DOMAIN)
        .chain_update(canonical)
        .finalize()
        .into()
}

fn root_from_leaves(leaves: &[[u8; 32]]) -> [u8; 32] {
    if leaves.is_empty() {
        return Sha256::digest([]).into();
    }

    let mut level = leaves.to_vec();
    while level.len() > 1 {
        if level.len() % 2 == 1 {
            level.push(*level.last().expect("non-empty level"));
        }
        level = level
            .chunks_exact(2)
            .map(|pair| {
                Sha256::new()
                    .chain_update(NODE_DOMAIN)
                    .chain_update(pair[0])
                    .chain_update(pair[1])
                    .finalize()
                    .into()
            })
            .collect();
    }
    level[0]
}

fn hex(bytes: &[u8]) -> String {
    let mut output = String::with_capacity(bytes.len() * 2);
    for byte in bytes {
        write!(output, "{byte:02x}").expect("writing to String cannot fail");
    }
    output
}

fn from_python(value: &Bound<'_, PyAny>, path: &str) -> PyResult<JsonValue> {
    from_python_inner(value, path, 0, &mut HashSet::new())
}

fn from_python_inner(
    value: &Bound<'_, PyAny>,
    path: &str,
    depth: usize,
    active_containers: &mut HashSet<usize>,
) -> PyResult<JsonValue> {
    if depth > 128 {
        return Err(PyValueError::new_err(format!(
            "{path}: nesting exceeds the maximum commitment depth of 128"
        )));
    }
    if value.is_none() {
        return Ok(JsonValue::Null);
    }
    if value.is_instance_of::<PyBool>() {
        return Ok(JsonValue::Bool(value.extract()?));
    }
    if value.is_instance_of::<PyInt>() {
        let decimal = value.str()?.to_str()?.to_owned();
        return Ok(JsonValue::Integer(decimal));
    }
    if value.is_instance_of::<PyString>() {
        return value
            .extract::<String>()
            .map(JsonValue::String)
            .map_err(|_| {
                PyValueError::new_err(format!("{path}: strings may not contain lone surrogates"))
            });
    }
    if let Ok(dict) = value.downcast::<PyDict>() {
        let identity = dict.as_ptr() as usize;
        if !active_containers.insert(identity) {
            return Err(PyValueError::new_err(format!(
                "{path}: circular references are not supported"
            )));
        }
        let mut entries = Vec::with_capacity(dict.len());
        for (key, child) in dict.iter() {
            let key = key.downcast::<PyString>().map_err(|_| {
                PyTypeError::new_err(format!("{path}: object keys must be strings"))
            })?;
            let key = key.extract::<String>().map_err(|_| {
                PyValueError::new_err(format!(
                    "{path}: object keys may not contain lone surrogates"
                ))
            })?;
            let child_path = format!("{path}.{key}");
            entries.push((
                key,
                from_python_inner(&child, &child_path, depth + 1, active_containers)?,
            ));
        }
        active_containers.remove(&identity);
        entries.sort_by(|left, right| left.0.cmp(&right.0));
        return Ok(JsonValue::Object(entries));
    }
    if let Ok(list) = value.downcast::<PyList>() {
        let identity = list.as_ptr() as usize;
        if !active_containers.insert(identity) {
            return Err(PyValueError::new_err(format!(
                "{path}: circular references are not supported"
            )));
        }
        let mut values = Vec::with_capacity(list.len());
        for (index, child) in list.iter().enumerate() {
            values.push(from_python_inner(
                &child,
                &format!("{path}[{index}]"),
                depth + 1,
                active_containers,
            )?);
        }
        active_containers.remove(&identity);
        return Ok(JsonValue::Array(values));
    }
    if let Ok(tuple) = value.downcast::<PyTuple>() {
        let identity = tuple.as_ptr() as usize;
        if !active_containers.insert(identity) {
            return Err(PyValueError::new_err(format!(
                "{path}: circular references are not supported"
            )));
        }
        let mut values = Vec::with_capacity(tuple.len());
        for (index, child) in tuple.iter().enumerate() {
            values.push(from_python_inner(
                &child,
                &format!("{path}[{index}]"),
                depth + 1,
                active_containers,
            )?);
        }
        active_containers.remove(&identity);
        return Ok(JsonValue::Array(values));
    }

    Err(PyTypeError::new_err(format!(
        "{path}: unsupported value type {}; expected JSON-safe null, bool, int, str, list, tuple, or string-keyed dict",
        value.get_type().name()?
    )))
}

#[pyclass(module = "watchllm_webproof._native")]
struct NativeAccumulator {
    leaves: Mutex<Vec<[u8; 32]>>,
    records: Mutex<Vec<Vec<u8>>>,
}

impl NativeAccumulator {
    fn locked<T>(mutex: &Mutex<T>) -> PyResult<MutexGuard<'_, T>> {
        mutex
            .lock()
            .map_err(|_| PyRuntimeError::new_err("native accumulator lock poisoned"))
    }
}

#[pymethods]
impl NativeAccumulator {
    #[new]
    fn new() -> Self {
        Self {
            leaves: Mutex::new(Vec::new()),
            records: Mutex::new(Vec::new()),
        }
    }

    fn record(&self, record: &Bound<'_, PyAny>) -> PyResult<()> {
        let value = from_python(record, "$record")?;
        if !matches!(value, JsonValue::Object(_)) {
            return Err(PyTypeError::new_err(
                "$record: record must be a mapping/dict",
            ));
        }
        let canonical = canonical_bytes(&value);
        let hash = leaf_hash(&canonical);
        // Keep both locks for one short atomic append so records and leaves cannot diverge.
        let mut leaves = Self::locked(&self.leaves)?;
        let mut records = Self::locked(&self.records)?;
        leaves.push(hash);
        records.push(canonical);
        Ok(())
    }

    fn records_json(&self) -> PyResult<Vec<Vec<u8>>> {
        Ok(Self::locked(&self.records)?.clone())
    }

    fn proof<'py>(&self, py: Python<'py>, session_id: &str) -> PyResult<Bound<'py, PyDict>> {
        let leaves = Self::locked(&self.leaves)?;
        let result = PyDict::new(py);
        result.set_item("proof_type", "local_merkle_stub")?;
        result.set_item("proof_version", "1.0.0")?;
        result.set_item("attestation", false)?;
        result.set_item("algorithm", "sha256-local-merkle-v1")?;
        result.set_item("aggregation_enabled", true)?;
        result.set_item("merkle_root", hex(&root_from_leaves(&leaves)))?;
        result.set_item("leaf_count", leaves.len())?;
        result.set_item("session_id", session_id)?;
        Ok(result)
    }
}

#[pyfunction]
fn canonical_leaf(record: &Bound<'_, PyAny>) -> PyResult<Vec<u8>> {
    Ok(canonical_bytes(&from_python(record, "$record")?))
}

#[pymodule]
fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<NativeAccumulator>()?;
    module.add_function(wrap_pyfunction!(canonical_leaf, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use proptest::prelude::*;

    fn string(value: &str) -> JsonValue {
        JsonValue::String(value.to_owned())
    }

    #[test]
    fn canonicalizes_python_compatible_ascii_json() {
        let value = JsonValue::Object(vec![
            ("z".into(), JsonValue::Null),
            (
                "a".into(),
                JsonValue::Array(vec![
                    JsonValue::Bool(true),
                    JsonValue::Integer("-2".into()),
                    string("é😀\n"),
                ]),
            ),
        ]);
        assert_eq!(
            String::from_utf8(canonical_bytes(&value)).unwrap(),
            r#"{"a":[true,-2,"\u00e9\ud83d\ude00\n"],"z":null}"#
        );
    }

    #[test]
    fn empty_root_is_sha256_of_empty_bytes() {
        assert_eq!(
            hex(&root_from_leaves(&[])),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        );
    }

    #[test]
    fn odd_levels_duplicate_the_last_node() {
        let leaves = [leaf_hash(b"a"), leaf_hash(b"b"), leaf_hash(b"c")];
        let first = Sha256::new()
            .chain_update(NODE_DOMAIN)
            .chain_update(leaves[0])
            .chain_update(leaves[1])
            .finalize();
        let second = Sha256::new()
            .chain_update(NODE_DOMAIN)
            .chain_update(leaves[2])
            .chain_update(leaves[2])
            .finalize();
        let expected: [u8; 32] = Sha256::new()
            .chain_update(NODE_DOMAIN)
            .chain_update(first)
            .chain_update(second)
            .finalize()
            .into();
        assert_eq!(root_from_leaves(&leaves), expected);
    }

    proptest! {
        #[test]
        fn canonical_object_order_is_deterministic(mut entries in prop::collection::vec(("[a-z]{1,8}", any::<i64>()), 0..30)) {
            entries.sort_by(|left, right| left.0.cmp(&right.0));
            entries.dedup_by(|left, right| left.0 == right.0);
            let forward = JsonValue::Object(entries.iter().map(|(key, value)| (key.clone(), JsonValue::Integer(value.to_string()))).collect());
            let reverse = JsonValue::Object(entries.iter().rev().map(|(key, value)| (key.clone(), JsonValue::Integer(value.to_string()))).collect());
            prop_assert_eq!(canonical_bytes(&forward), canonical_bytes(&reverse));
        }

        #[test]
        fn merkle_root_is_deterministic(records in prop::collection::vec(prop::collection::vec(any::<u8>(), 0..128), 0..64)) {
            let leaves: Vec<_> = records.iter().map(|record| leaf_hash(record)).collect();
            prop_assert_eq!(root_from_leaves(&leaves), root_from_leaves(&leaves));
        }
    }
}
