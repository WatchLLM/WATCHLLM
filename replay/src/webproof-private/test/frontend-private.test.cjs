const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');

test('private frontend builds outside exported source tree and exposes required routes', () => {
  const result = spawnSync('npx', ['--no-install', 'vite', 'build', '--config', 'src/webproof-private/vite.config.ts'], {
    encoding: 'utf8',
    shell: process.platform === 'win32',
  });
  assert.equal(result.status, 0, `${result.stdout}\n${result.stderr}`);
  assert.equal(
    fs.existsSync(path.join(__dirname, '../../../.private-build/webproof-dashboard/index.html')),
    true
  );
  const trackedDist = spawnSync('git', ['ls-files', 'replay/src/client/dist'], {
    cwd: path.join(__dirname, '../../../..'),
    encoding: 'utf8',
  });
  assert.equal(trackedDist.stdout.trim(), '', 'private bundle must not enter tracked public dist');
  const app = fs.readFileSync(path.join(__dirname, '../client/App.tsx'), 'utf8');
  assert.match(app, /path="\/proofs"/);
  assert.match(app, /path="\/proof\/:id"/);
});
