use criterion::{black_box, criterion_group, criterion_main, Criterion};
use watchllm_core::engine::evaluate_source;
use watchllm_core::parser::SourceLanguage;

fn bench_allowed_typescript(c: &mut Criterion) {
    let source = r#"
        import express from "express";

        const message = "hello";

        function handler() {
            auth.verify(token);
            db.query("SELECT 1");
        }
    "#;

    c.bench_function("evaluate_allowed_typescript", |b| {
        b.iter(|| evaluate_source(black_box(source), SourceLanguage::TypeScript, None, "enforce"))
    });
}

fn bench_violating_typescript(c: &mut Criterion) {
    let source = r#"
        import childProcess from "child_process";
        import { connect } from "@internal/db";

        const apiKey = "sk_live_123";

        function handler() {
            db.query("SELECT 1");
            auth.verify(token);
        }
    "#;

    c.bench_function("evaluate_violating_typescript", |b| {
        b.iter(|| evaluate_source(black_box(source), SourceLanguage::TypeScript, None, "enforce"))
    });
}

criterion_group!(
    benches,
    bench_allowed_typescript,
    bench_violating_typescript
);

criterion_main!(benches);
