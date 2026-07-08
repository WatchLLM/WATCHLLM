/**
 * Singleton Wasm module loader for the WatchLLM VS Code extension.
 *
 * Handles:
 *   - Lazy initialisation (first call loads the module)
 *   - Caching (subsequent calls reuse the loaded module)
 *   - Graceful fallback: if the Wasm binary is missing or fails to load,
 *     `isAvailable()` returns false and the caller falls back to Python subprocess.
 *
 * The real Wasm binary ships as:
 *   runtime/crates/wasm/pkg/watchllm_wasm_bg.wasm   (binary)
 *   runtime/crates/wasm/pkg/watchllm_wasm.js         (wasm-bindgen glue)
 *
 * The JS glue is require()'d at runtime so that the extension does not crash
 * during development when the binary has not been compiled yet.
 */

/** JSON shape returned by the real Rust Wasm binary (from core/src/models.rs). */
export interface WasmKernelResult {
    status: 'ok' | 'error';
    exit_code: 0 | 1 | 2;
    payload: {
        allowed: boolean;
        violations: Array<{
            message: string;
            rule: string;
            line: number;
            column: number;
            severity: string;
        }>;
    } | null;
    error: string | null;
}

type WasmModule = {
    evaluate_source: (source: string, configJson: string) => string;
};

let _module: WasmModule | null = null;
let _loadAttempted = false;
let _available = false;

/**
 * Attempt to load the Wasm module. Safe to call multiple times.
 * Returns the module on success, null on failure.
 */
function _tryLoad(): WasmModule | null {
    if (_loadAttempted) {
        return _available ? _module : null;
    }

    _loadAttempted = true;

    try {
        // Dynamic require keeps the extension from crashing when the .wasm
        // binary has not been built yet.
        const mod = require('../../runtime/crates/wasm/pkg/watchllm_wasm.js') as WasmModule;

        if (typeof mod?.evaluate_source !== 'function') {
            console.warn('[WatchLLM] Wasm module loaded but evaluate_source is not a function — falling back to Python.');
            return null;
        }

        // Smoke-test: run a trivial evaluation to confirm the binary works.
        const testResult = mod.evaluate_source('const x = 1;', JSON.stringify({ language: 'javascript' }));
        JSON.parse(testResult); // throws if output is not valid JSON

        _module = mod;
        _available = true;
        console.log('[WatchLLM] Wasm kernel loaded successfully.');
        return _module;
    } catch (error) {
        console.warn(`[WatchLLM] Wasm kernel unavailable — falling back to Python subprocess. Reason: ${error instanceof Error ? error.message : String(error)}`);
        _available = false;
        return null;
    }
}

/** Returns true if the Wasm module is available for use. */
export function isAvailable(): boolean {
    _tryLoad();
    return _available;
}

/**
 * Evaluate source using the Wasm kernel.
 *
 * @param source    Source code text.
 * @param language  Language identifier (e.g. 'javascript', 'typescript', 'python').
 * @returns Parsed WasmKernelResult, or null if the module failed to load.
 */
export function evaluate(source: string, language: string): WasmKernelResult | null {
    const mod = _tryLoad();
    if (!mod) {
        return null;
    }

    try {
        const configJson = JSON.stringify({ language, sourceLanguage: language });
        const resultJson = mod.evaluate_source(source, configJson);
        return JSON.parse(resultJson) as WasmKernelResult;
    } catch (error) {
        console.error(`[WatchLLM] Wasm evaluation error: ${error instanceof Error ? error.message : String(error)}`);
        // Mark as unavailable so subsequent calls go to Python path.
        _available = false;
        return null;
    }
}

/** Reset the loader state (for testing). */
export function _reset(): void {
    _module = null;
    _loadAttempted = false;
    _available = false;
}
