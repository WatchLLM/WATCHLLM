use std::io::{self, Read};
use std::path::PathBuf;
use std::process::ExitCode;

use clap::Parser;
use watchllm_core::engine;
use watchllm_core::models::KernelExecutionResult;

#[derive(Debug, Parser)]
#[command(name = "watchllm-cli")]
#[command(about = "WatchLLM native runtime CLI")]
struct Args {
    #[arg(long)]
    filepath: Option<PathBuf>,

    #[arg(long)]
    stdin: bool,

    #[arg(long)]
    json: bool,

    #[arg(long, default_value = "auto")]
    language: String,

    #[arg(long, default_value = "enforce")]
    mode: String,
}

fn main() -> ExitCode {
    let args = Args::parse();

    let result = evaluate_cli_request(&args);
    emit_result(&result, args.json);

    ExitCode::from(normalise_exit_code(result.exit_code()))
}

fn evaluate_cli_request(args: &Args) -> KernelExecutionResult {
    let (source, file_path) = if args.stdin {
        let mut source = String::new();
        if let Err(err) = io::stdin().read_to_string(&mut source) {
            return cli_error(format!("Failed to read stdin: {}", err));
        }
        (source, None)
    } else if let Some(filepath) = &args.filepath {
        match std::fs::read_to_string(filepath) {
            Ok(source) => (source, Some(filepath.to_string_lossy().to_string())),
            Err(err) => return cli_error(format!("Failed to read file: {}", err)),
        }
    } else {
        return cli_error("Either --filepath or --stdin is required".to_string());
    };

    let language = resolve_language(&args.language, file_path.as_deref());

    engine::evaluate_source_with_language_name(&source, &language, file_path.as_deref(), &args.mode)
}

fn resolve_language(language: &str, file_path: Option<&str>) -> String {
    match language {
        l if l == "auto" || l.is_empty() => {
            if let Some(path) = file_path {
                let lower = path.to_lowercase();
                if lower.ends_with(".ts") || lower.ends_with(".tsx") {
                    return "typescript".to_string();
                }
                if lower.ends_with(".js") || lower.ends_with(".mjs") || lower.ends_with(".cjs") {
                    return "javascript".to_string();
                }
            }
            "typescript".to_string()
        }
        "js" | "javascript" => "javascript".to_string(),
        "ts" | "typescript" => "typescript".to_string(),
        "tsx" => "tsx".to_string(),
        _ => language.to_string(),
    }
}

fn emit_result(result: &KernelExecutionResult, json_mode: bool) {
    if json_mode {
        println!("{}", serialize_result(result));
        return;
    }

    if let Some(err) = &result.error {
        eprintln!("Error: {}", err);
        return;
    }

    if result.decision == "ALLOW" {
        println!("allowed");
    } else {
        println!("blocked");
        for rr in &result.rule_results {
            for violation in &rr.violations {
                println!(
                    "{}:{} [{}] {}",
                    violation.location.line,
                    violation.location.column,
                    rr.rule_id,
                    violation.message
                );
            }
        }
    }
}

fn serialize_result(result: &KernelExecutionResult) -> String {
    serde_json::to_string(result).unwrap_or_else(|err| {
        format!(
            r#"{{"decision":"ALLOW","mode":"enforce","language":"javascript","rule_results":[],"error":"Result serialization error: {}"}}"#,
            err.to_string().replace('\\', "\\\\").replace('"', "\\\"")
        )
    })
}

fn cli_error(message: String) -> KernelExecutionResult {
    KernelExecutionResult {
        decision: "ALLOW".to_string(),
        mode: "enforce".to_string(),
        file_path: None,
        language: "javascript".to_string(),
        rule_results: vec![],
        error: Some(message),
    }
}

fn normalise_exit_code(exit_code: i32) -> u8 {
    match exit_code {
        0 => 0,
        1 => 1,
        _ => 2,
    }
}
