use std::io::{self, Read};
use std::process::ExitCode;

use clap::Parser;
use watchllm_core::engine;
use watchllm_core::models::KernelExecutionResult;

#[derive(Debug, Parser)]
#[command(name = "watchllm-cli")]
#[command(about = "WatchLLM native runtime CLI")]
struct Args {
    #[arg(long)]
    stdin: bool,

    #[arg(long)]
    json: bool,

    #[arg(long, default_value = "typescript")]
    language: String,
}

fn main() -> ExitCode {
    let args = Args::parse();

    let result = evaluate_cli_request(&args);
    emit_result(&result, args.json);

    ExitCode::from(normalise_exit_code(result.exit_code))
}

fn evaluate_cli_request(args: &Args) -> KernelExecutionResult {
    if !args.stdin {
        return cli_error("--stdin is required".to_string());
    }

    let mut source = String::new();

    if let Err(err) = io::stdin().read_to_string(&mut source) {
        return cli_error(format!("Failed to read stdin: {}", err));
    }

    engine::evaluate_source_with_language_name(&source, &args.language)
}

fn emit_result(result: &KernelExecutionResult, json_mode: bool) {
    if json_mode {
        println!("{}", serialize_result(result));
        return;
    }

    if result.status == "error" {
        eprintln!(
            "{}",
            result
                .error
                .as_deref()
                .unwrap_or("Unknown WatchLLM runtime error")
        );
        return;
    }

    let Some(payload) = result.payload.as_ref() else {
        eprintln!("Missing result payload");
        return;
    };

    if payload.allowed {
        println!("allowed");
    } else {
        println!("blocked");

        for violation in &payload.violations {
            println!(
                "{}:{} [{}] {}",
                violation.line, violation.column, violation.rule, violation.message
            );
        }
    }
}

fn serialize_result(result: &KernelExecutionResult) -> String {
    serde_json::to_string(result).unwrap_or_else(|err| {
        let escaped = format!("Result serialization error: {}", err)
            .replace('\\', "\\\\")
            .replace('"', "\\\"");

        format!(
            r#"{{"status":"error","exit_code":2,"payload":null,"error":"{}"}}"#,
            escaped
        )
    })
}

fn cli_error(message: String) -> KernelExecutionResult {
    KernelExecutionResult {
        status: "error".to_string(),
        exit_code: 2,
        payload: None,
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
