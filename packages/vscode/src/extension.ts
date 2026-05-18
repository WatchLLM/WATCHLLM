import * as vscode from 'vscode';
import { spawn } from 'node:child_process';

type WatchLLMResult = {
  stdout: string;
  stderr: string;
};

function runWatchLLM(cwd: string, args: string[], input: string): Promise<WatchLLMResult> {
  return new Promise((resolve, reject) => {
    const child = spawn('python', args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
    });

    let stdout = '';
    let stderr = '';

    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');

    child.stdout.on('data', (chunk: string) => {
      stdout += chunk;
    });

    child.stderr.on('data', (chunk: string) => {
      stderr += chunk;
    });

    child.on('error', (error) => {
      const enriched = error as Error & { stdout?: string; stderr?: string };
      enriched.stdout = stdout;
      enriched.stderr = stderr;
      reject(enriched);
    });

    child.on('close', (code) => {
      if (code === 0) {
        resolve({ stdout, stderr });
        return;
      }

      const error = new Error(stderr.trim() || stdout.trim() || 'WatchLLM blocked save') as Error & {
        stdout?: string;
        stderr?: string;
      };

      error.stdout = stdout;
      error.stderr = stderr;
      reject(error);
    });

    child.stdin.write(input);
    child.stdin.end();
  });
}

export function activate(context: vscode.ExtensionContext): void {
  const outputChannel = vscode.window.createOutputChannel('WatchLLM');

  const disposable = vscode.workspace.onWillSaveTextDocument((event) => {
    if (event.document.uri.scheme !== 'file') {
      return;
    }

    const workspaceFolder = vscode.workspace.getWorkspaceFolder(event.document.uri);

    if (!workspaceFolder) {
      return;
    }

    event.waitUntil(
      runWatchLLM(
        workspaceFolder.uri.fsPath,
        ['cli/main.py', 'check', event.document.fileName, '--local-only', '--stdin'],
        event.document.getText(),
      )
        .then((result) => {
          if (
            typeof result.stdout === 'string' &&
            result.stdout.includes('WatchLLM shadow violations')
          ) {
            outputChannel.clear();
            outputChannel.appendLine(result.stdout.trim());
            outputChannel.show(true);

            vscode.window.showWarningMessage(
              'WatchLLM found shadow-mode violations. Save was allowed.',
            );
          }

          return [];
        })
        .catch((error: unknown) => {
          const result = error as { stdout?: unknown; stderr?: unknown };
          let message = error instanceof Error ? error.message : 'WatchLLM blocked save';

          if (typeof result.stderr === 'string' && result.stderr.trim()) {
            message = result.stderr.trim();
          } else if (typeof result.stdout === 'string' && result.stdout.trim()) {
            message = result.stdout.trim();
          }

          outputChannel.clear();
          outputChannel.appendLine(message);
          outputChannel.show(true);

          vscode.window.showErrorMessage(
            'WatchLLM blocked save. See WatchLLM output for rule, location, and reason.',
          );

          throw new Error(message);
        }),
    );
  });

  context.subscriptions.push(outputChannel, disposable);
}

export function deactivate(): void {}
