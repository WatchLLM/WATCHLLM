'use strict';
const crypto = require('node:crypto');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

const HASH_RE = /^(?:0x)?[0-9a-fA-F]{64}$/;
const ID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const SESSION_RE = /^[A-Za-z0-9._:-]{1,64}$/;
const RUN_RE = /^[A-Za-z0-9._:-]{1,128}$/;
const NODE_DOMAIN = Buffer.from('watchllm-webproof-local-node-v1\0');
const STATUSES = new Set(['stored', 'queued', 'processing', 'submitted', 'anchored', 'failed']);
const CHAINS = new Set(['base-sepolia', 'base-mainnet']);
const MAX_RAW = 16_384;
const REDACT_KEY = /authorization|cookie|secret|token|password|api[_-]?key|signature|r2|signer|rpc/i;

function migrate(db) {
  db.exec(`
    CREATE TABLE IF NOT EXISTS webproof_proofs (
      id TEXT PRIMARY KEY, session_id TEXT NOT NULL, target_domain TEXT NOT NULL,
      target_path TEXT NOT NULL, observed_at INTEGER NOT NULL, status TEXT NOT NULL,
      verification_mode TEXT NOT NULL CHECK (verification_mode = 'commitment_only'),
      attestation INTEGER NOT NULL CHECK (attestation = 0), proof_type TEXT NOT NULL,
      proof_version TEXT NOT NULL, leaf_hash TEXT NOT NULL, leaf_index INTEGER NOT NULL,
      merkle_root TEXT NOT NULL, merkle_path TEXT NOT NULL, response_hash TEXT NOT NULL,
      chain TEXT NOT NULL, tx_hash TEXT, confirmations INTEGER NOT NULL DEFAULT 0,
      required_confirmations INTEGER NOT NULL DEFAULT 0, raw_proof TEXT,
      immutable_snapshot TEXT,
      worker_updated_at INTEGER, refreshed_at INTEGER, created_at INTEGER NOT NULL,
      updated_at INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS step_proofs (
      run_id TEXT NOT NULL, step_id TEXT NOT NULL, proof_id TEXT NOT NULL,
      created_at INTEGER NOT NULL,
      PRIMARY KEY (run_id, step_id, proof_id),
      FOREIGN KEY (run_id) REFERENCES runs(id), FOREIGN KEY (step_id) REFERENCES steps(id),
      FOREIGN KEY (proof_id) REFERENCES webproof_proofs(id)
    );
    CREATE INDEX IF NOT EXISTS idx_webproof_session_order ON webproof_proofs(session_id, observed_at DESC, id ASC);
    CREATE INDEX IF NOT EXISTS idx_step_proofs_run_step ON step_proofs(run_id, step_id);
  `);
  const columns = new Set(db.prepare('PRAGMA table_info(webproof_proofs)').all().map((column) => column.name));
  if (!columns.has('immutable_snapshot')) db.exec('ALTER TABLE webproof_proofs ADD COLUMN immutable_snapshot TEXT');
  const backfill = db.prepare('UPDATE webproof_proofs SET immutable_snapshot=? WHERE id=?');
  for (const row of db.prepare('SELECT * FROM webproof_proofs WHERE immutable_snapshot IS NULL AND raw_proof IS NOT NULL').all()) {
    try {
      const proof = JSON.parse(row.raw_proof);
      backfill.run(immutableSnapshot(proof, proof.leaf_data || {}, Number(proof.leaf_data?.timestamp)), row.id);
    } catch { /* A truncated legacy snapshot cannot safely claim an immutable identity. */ }
  }
}

function normalizeHash(value, field) {
  if (typeof value !== 'string' || !HASH_RE.test(value)) throw input(`${field} must be a 32-byte hex hash`);
  return `0x${value.replace(/^0x/, '').toLowerCase()}`;
}
function input(message, status = 400) { const error = new Error(message); error.status = status; return error; }
function nodeHash(left, right) {
  return `0x${crypto.createHash('sha256').update(NODE_DOMAIN).update(Buffer.from(left.slice(2), 'hex')).update(Buffer.from(right.slice(2), 'hex')).digest('hex')}`;
}
function verifyPath(leafHash, leafIndex, merklePath, root) {
  let computed = normalizeHash(leafHash, 'leaf_hash');
  let index = leafIndex;
  const ladder = [];
  for (let level = 0; level < merklePath.length; level += 1) {
    const sibling = normalizeHash(merklePath[level], `merkle_path[${level}]`);
    const side = (index & 1) === 0 ? 'right' : 'left';
    computed = side === 'right' ? nodeHash(computed, sibling) : nodeHash(sibling, computed);
    ladder.push({ level, sibling, siblingSide: side, computedParent: computed });
    index = Math.floor(index / 2);
  }
  return { valid: computed === normalizeHash(root, 'merkle_root'), computedRoot: computed, ladder };
}
function safeUrl(domain, targetPath) {
  if (typeof domain !== 'string' || domain.length > 253 || domain !== domain.toLowerCase() || !/^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)*[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(domain)) throw input('target_domain must be a lowercase DNS hostname');
  if (typeof targetPath !== 'string' || targetPath.length > 2048 || !targetPath.startsWith('/') || /[?#]/.test(targetPath)) throw input('path must be absolute without query or fragment');
  return `${domain}${targetPath}`;
}
function redact(value, depth = 0) {
  if (depth > 8) return '[DEPTH REDACTED]';
  if (typeof value === 'string') return value.length > 2048 ? `${value.slice(0, 2048)}…[TRUNCATED]` : value.replace(/(bearer\s+)[A-Za-z0-9._~+/=-]+/gi, '$1[REDACTED]');
  if (Array.isArray(value)) return value.slice(0, 128).map((v) => redact(v, depth + 1));
  if (value && typeof value === 'object') return Object.fromEntries(Object.entries(value).slice(0, 128).map(([k, v]) => [k, REDACT_KEY.test(k) ? '[REDACTED]' : redact(v, depth + 1)]));
  return value;
}
function boundedRaw(value) {
  if (value == null) return null;
  let text = JSON.stringify(redact(value), null, 2);
  if (Buffer.byteLength(text) > MAX_RAW) text = `${Buffer.from(text).subarray(0, MAX_RAW).toString('utf8')}\n…[TRUNCATED]`;
  return text;
}
function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
  return value;
}
// A verification ID names one immutable snapshot. Its identity is all accepted,
// redacted proof content except Worker-refreshed lifecycle fields. Known hashes
// and defaults are canonicalized so equivalent wire encodings remain idempotent.
function immutableSnapshot(p, target, observed) {
  const snapshot = redact(p);
  for (const field of ['status', 'l2_transaction_hash', 'confirmations', 'required_confirmations', 'updated_at', 'worker_updated_at', 'refreshed_at']) delete snapshot[field];
  Object.assign(snapshot, {
    verification_id: p.verification_id,
    session_id: p.session_id,
    proof_type: 'local_merkle_stub',
    proof_version: p.proof_version || '1.0.0',
    verification_mode: 'commitment_only',
    attestation: false,
    leaf_hash: normalizeHash(p.leaf_hash, 'leaf_hash'),
    leaf_index: p.leaf_index,
    merkle_root: normalizeHash(p.merkle_root, 'merkle_root'),
    merkle_path: p.merkle_path.map((hash, index) => normalizeHash(hash, `merkle_path[${index}]`)),
    chain: p.chain,
    leaf_data: {
      ...redact(target),
      target_domain: target.target_domain,
      path: target.path,
      response_hash: normalizeHash(target.response_hash, 'response_hash'),
      timestamp: observed,
    },
  });
  return JSON.stringify(stableValue(snapshot));
}
function sameSnapshot(left, right) {
  return typeof left === 'string' && left.length === right.length && crypto.timingSafeEqual(Buffer.from(left), Buffer.from(right));
}
function conflict() { return input('proof snapshot conflicts with existing verification id', 409); }
function validateRecord(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) throw input('body must be an object');
  const p = body.proof;
  if (!p || typeof p !== 'object' || Array.isArray(p)) throw input('proof is required');
  if (!ID_RE.test(String(p.verification_id || ''))) throw input('invalid verification_id');
  if (!SESSION_RE.test(String(p.session_id || ''))) throw input('invalid session_id');
  if (p.proof_type !== 'local_merkle_stub' || p.verification_mode !== 'commitment_only' || p.attestation !== false) throw input('only local_merkle_stub commitment_only attestation:false is supported');
  if (!Number.isSafeInteger(p.leaf_index) || p.leaf_index < 0) throw input('invalid leaf_index');
  if (!Array.isArray(p.merkle_path) || p.merkle_path.length > 64) throw input('invalid merkle_path');
  const target = p.leaf_data || {};
  safeUrl(target.target_domain, target.path);
  const observed = Number(target.timestamp);
  if (!Number.isSafeInteger(observed) || observed < 946684800000 || observed > Date.now() + 300000) throw input('invalid timestamp');
  if (!CHAINS.has(p.chain)) throw input('invalid chain');
  const verification = verifyPath(p.leaf_hash, p.leaf_index, p.merkle_path, p.merkle_root);
  if (!verification.valid) throw input('merkle inclusion path does not match root');
  const status = p.status || 'queued'; if (!STATUSES.has(status)) throw input('invalid status');
  return { p, target, observed, verification };
}
function noStore(res) { res.set('Cache-Control', 'no-store, max-age=0'); res.set('Pragma', 'no-cache'); }
function freshness(row, now, staleMs) {
  if (!row.refreshed_at) return { state: 'snapshot', stale: true, refreshedAt: null };
  return { state: now - row.refreshed_at <= staleMs ? 'live' : 'stale', stale: now - row.refreshed_at > staleMs, refreshedAt: row.refreshed_at };
}
function mapRow(row, staleMs, detail = false) {
  const proof = { id: row.id, sessionId: row.session_id, url: safeUrl(row.target_domain, row.target_path), targetDomain: row.target_domain, path: row.target_path, observedAt: row.observed_at, status: row.status, source: freshness(row, Date.now(), staleMs), verificationMode: row.verification_mode, attestation: false, proofType: row.proof_type, proofVersion: row.proof_version, chain: row.chain, l2TransactionHash: row.tx_hash, confirmations: row.confirmations, requiredConfirmations: row.required_confirmations };
  if (detail) {
    const merklePath = JSON.parse(row.merkle_path);
    proof.merkle = { leafHash: row.leaf_hash, leafIndex: row.leaf_index, root: row.merkle_root, path: merklePath, ...verifyPath(row.leaf_hash, row.leaf_index, merklePath, row.merkle_root) };
    proof.responseHash = row.response_hash;
    proof.rawProof = row.raw_proof;
    proof.disclaimer = 'Commitment-only local Merkle proof (attestation:false). Local path verification does not attest the remote response, target identity, transport, or signer.';
  }
  return proof;
}
function constantToken(req, expected) {
  const supplied = req.get('X-Replay-Ingest-Token') || '';
  if (!expected || !supplied || supplied.length !== expected.length || !crypto.timingSafeEqual(Buffer.from(supplied), Buffer.from(expected))) throw input('not found', 404);
}
function statusRank(status) { return ({ stored: 0, queued: 1, processing: 2, submitted: 3, anchored: 4, failed: 4 })[status] ?? -1; }
function applyWorker(db, row, data, now) {
  if (!data || typeof data !== 'object' || data.verification_id !== row.id || !STATUSES.has(data.status) || data.verification_mode !== 'commitment_only' || data.attestation !== false || normalizeHash(data.merkle_root, 'merkle_root') !== row.merkle_root || !CHAINS.has(data.chain)) throw input('invalid upstream response', 502);
  let nextStatus = row.status;
  if (statusRank(data.status) >= statusRank(row.status) && !(row.status === 'failed' && data.status !== 'failed') && !(row.status === 'anchored' && data.status !== 'anchored')) nextStatus = data.status;
  db.prepare(`UPDATE webproof_proofs SET status=?, tx_hash=?, confirmations=?, required_confirmations=?, worker_updated_at=?, refreshed_at=?, updated_at=? WHERE id=?`).run(nextStatus, typeof data.l2_transaction_hash === 'string' ? data.l2_transaction_hash : row.tx_hash, Number.isSafeInteger(data.confirmations) ? data.confirmations : row.confirmations, Number.isSafeInteger(data.required_confirmations) ? data.required_confirmations : row.required_confirmations, Number.isSafeInteger(data.updated_at) ? data.updated_at : null, now, now, row.id);
}
async function refreshKnown(db, row, options) {
  if (!options.workerBaseUrl || !options.workerApiKey) return { available: false };
  const controller = new AbortController(); const timer = setTimeout(() => controller.abort(), options.timeoutMs);
  try {
    const url = `${options.workerBaseUrl.replace(/\/$/, '')}/proof/${encodeURIComponent(row.id)}`;
    const response = await options.fetch(url, { headers: { Authorization: `Bearer ${options.workerApiKey}`, Accept: 'application/json' }, signal: controller.signal });
    if (!response.ok) throw new Error('upstream unavailable');
    const length = Number(response.headers.get('content-length')); if (Number.isFinite(length) && length > options.maxBytes) throw new Error('upstream response too large');
    const bytes = Buffer.from(await response.arrayBuffer()); if (bytes.length > options.maxBytes) throw new Error('upstream response too large');
    let data; try { data = JSON.parse(bytes.toString('utf8')); } catch { throw new Error('upstream malformed'); }
    applyWorker(db, row, data, Date.now()); return { available: true };
  } finally { clearTimeout(timer); }
}
function createProofExtension({ db, fetchImpl = globalThis.fetch, env = process.env } = {}) {
  migrate(db);
  const options = { workerBaseUrl: env.WEBPROOF_WORKER_BASE_URL || '', workerApiKey: env.WEBPROOF_WORKER_API_KEY || '', ingestToken: env.REPLAY_WEBPROOF_INGEST_TOKEN || '', timeoutMs: Math.min(Number(env.WEBPROOF_TIMEOUT_MS) || 2500, 10000), maxBytes: Math.min(Number(env.WEBPROOF_MAX_RESPONSE_BYTES) || 65536, 262144), staleMs: Math.max(Number(env.WEBPROOF_STALE_MS) || 300000, 1000), fetch: fetchImpl };
  async function maybeRefresh(row) { try { return await refreshKnown(db, row, options); } catch { return { available: false }; } }
  function mount(app) {
    app.post('/api/internal/proofs/snapshot', (req, res, next) => { try {
      constantToken(req, options.ingestToken); const { p, target, observed } = validateRecord(req.body); const now = Date.now();
      const snapshot = immutableSnapshot(p, target, observed);
      const runId = req.body.run_id; const stepId = req.body.step_id;
      if ((runId == null) !== (stepId == null)) throw input('run_id and step_id must be supplied together');
      if (runId != null && (!RUN_RE.test(runId) || !RUN_RE.test(stepId))) throw input('invalid run or step id');
      const transaction = db.transaction(() => {
        const existing = db.prepare('SELECT immutable_snapshot FROM webproof_proofs WHERE id=?').get(p.verification_id);
        if (existing && !sameSnapshot(existing.immutable_snapshot, snapshot)) throw conflict();
        if (!existing) db.prepare(`INSERT INTO webproof_proofs(id,session_id,target_domain,target_path,observed_at,status,verification_mode,attestation,proof_type,proof_version,leaf_hash,leaf_index,merkle_root,merkle_path,response_hash,chain,tx_hash,confirmations,required_confirmations,raw_proof,immutable_snapshot,worker_updated_at,refreshed_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)`).run(p.verification_id,p.session_id,target.target_domain,target.path,observed,p.status||'queued','commitment_only',0,'local_merkle_stub',p.proof_version||'1.0.0',normalizeHash(p.leaf_hash,'leaf_hash'),p.leaf_index,normalizeHash(p.merkle_root,'merkle_root'),JSON.stringify(p.merkle_path.map((h,i)=>normalizeHash(h,`merkle_path[${i}]`))),normalizeHash(target.response_hash,'response_hash'),p.chain,p.l2_transaction_hash||null,p.confirmations||0,p.required_confirmations||0,boundedRaw(p),snapshot,null,null,now,now);
        if (runId != null) {
          const owner = db.prepare('SELECT 1 FROM steps WHERE id=? AND run_id=?').get(stepId, runId); if (!owner) throw input('step does not belong to run');
          const associatedRun = db.prepare('SELECT run_id FROM step_proofs WHERE proof_id=? LIMIT 1').get(p.verification_id);
          if (associatedRun && associatedRun.run_id !== runId) throw conflict();
          db.prepare('INSERT OR IGNORE INTO step_proofs(run_id,step_id,proof_id,created_at) VALUES(?,?,?,?)').run(runId,stepId,p.verification_id,now);
        }
      }); transaction(); noStore(res); res.status(201).json({ proof: mapRow(db.prepare('SELECT * FROM webproof_proofs WHERE id=?').get(p.verification_id), options.staleMs, true) });
    } catch (error) { next(error); } });
    app.get('/api/proofs', async (req, res, next) => { try {
      const sessionId = req.query.session_id; const runId = req.query.run_id;
      if (!sessionId && !runId) throw input('session_id or run_id is required');
      if (sessionId && !SESSION_RE.test(sessionId)) throw input('invalid session_id'); if (runId && !RUN_RE.test(runId)) throw input('invalid run_id');
      const page = Number(req.query.page || 1), pageSize = Number(req.query.page_size || 25); if (!Number.isInteger(page)||page<1||page>100000||!Number.isInteger(pageSize)||pageSize<1||pageSize>100) throw input('invalid pagination');
      const join = runId ? 'JOIN step_proofs sp ON sp.proof_id=p.id' : ''; const filters=[]; const values=[]; if(sessionId){filters.push('p.session_id=?');values.push(sessionId)} if(runId){filters.push('sp.run_id=?');values.push(runId)}
      const where=`WHERE ${filters.join(' AND ')}`; const total=db.prepare(`SELECT COUNT(DISTINCT p.id) n FROM webproof_proofs p ${join} ${where}`).get(...values).n;
      const rows=db.prepare(`SELECT DISTINCT p.* FROM webproof_proofs p ${join} ${where} ORDER BY p.observed_at DESC,p.id ASC LIMIT ? OFFSET ?`).all(...values,pageSize,(page-1)*pageSize);
      noStore(res); res.json({proofs:rows.map(r=>mapRow(r,options.staleMs)),pagination:{page,pageSize,total,totalPages:Math.ceil(total/pageSize)}});
    } catch(error){next(error)} });
    app.get('/api/proofs/:id', async (req,res,next)=>{try{if(!ID_RE.test(req.params.id))throw input('not found',404);let row=db.prepare('SELECT * FROM webproof_proofs WHERE id=?').get(req.params.id);if(!row)throw input('not found',404);const refreshed=await maybeRefresh(row);row=db.prepare('SELECT * FROM webproof_proofs WHERE id=?').get(req.params.id);if(!refreshed.available&&!row)throw input('proof unavailable',503);noStore(res);res.json({proof:mapRow(row,options.staleMs,true)});}catch(e){next(e)}});
    app.get('/api/proofs/:id/download', async (req,res,next)=>{try{if(!ID_RE.test(req.params.id))throw input('not found',404);const row=db.prepare('SELECT * FROM webproof_proofs WHERE id=?').get(req.params.id);if(!row)throw input('not found',404);const proof=mapRow(row,options.staleMs,true);const modulePath=pathToFileURL(path.join(__dirname,'pdf.mjs')).href;const { renderAuditPdf }=await import(modulePath);const pdf=await renderAuditPdf(proof);noStore(res);res.set('Content-Type','application/pdf');res.set('Content-Disposition',`attachment; filename="Audit-Report-Agent-Session-${encodeURIComponent(row.session_id)}.pdf"; filename*=UTF-8''Audit%20Report%20-%20Agent%20Session%20%23${encodeURIComponent(row.session_id)}.pdf`);res.send(pdf);}catch(e){next(e)}});
    app.get('/api/webproof/runs/:runId/associations', (req, res, next) => { try {
      if (!RUN_RE.test(req.params.runId)) throw input('not found', 404);
      const run = db.prepare('SELECT 1 FROM runs WHERE id=?').get(req.params.runId);
      if (!run) throw input('not found', 404);
      const rows = db.prepare('SELECT step_id, proof_id FROM step_proofs WHERE run_id=? ORDER BY step_id, proof_id').all(req.params.runId);
      const steps = {}; for (const row of rows) (steps[row.step_id] ||= []).push(row.proof_id);
      noStore(res); res.json({ steps });
    } catch (error) { next(error); } });
    app.use((error, _req, res, _next) => {
      noStore(res);
      const status = Number.isInteger(error.status) && error.status >= 400 && error.status < 600 ? error.status : 500;
      res.status(status).json({ error: status === 500 ? 'internal error' : error.message });
    });
  }
  function enhanceGraph(runId, nodes) { const rows=db.prepare('SELECT step_id,proof_id FROM step_proofs WHERE run_id=? ORDER BY proof_id').all(runId);const by=new Map();for(const row of rows){const list=by.get(row.step_id)||[];list.push(row.proof_id);by.set(row.step_id,list)}return nodes.map(node=>({...node,proofs:by.get(node.id)||[],proofCount:(by.get(node.id)||[]).length})); }
  return { mount, enhanceGraph, verifyPath, boundedRaw, refreshKnown: (row)=>refreshKnown(db,row,options) };
}
module.exports={createProofExtension,verifyPath,boundedRaw,migrate,nodeHash};
