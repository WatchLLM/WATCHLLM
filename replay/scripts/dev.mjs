import { spawn } from 'node:child_process';

const npm = process.platform === 'win32' ? 'npm.cmd' : 'npm';
const children = [
  spawn(npm, ['run', 'dev:backend'], { stdio: 'inherit' }),
  spawn(npm, ['run', 'dev:frontend'], { stdio: 'inherit' }),
];

let shuttingDown = false;
function stop(signal = 'SIGTERM') {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of children) {
    if (!child.killed) child.kill(signal);
  }
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => stop(signal));
}

for (const child of children) {
  child.on('error', (error) => {
    console.error(error);
    stop();
    process.exitCode = 1;
  });
  child.on('exit', (code, signal) => {
    if (!shuttingDown) {
      process.exitCode = code ?? (signal ? 1 : 0);
      stop();
    }
  });
}
