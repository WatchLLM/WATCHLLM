import type { Env, ProofRow, ValidatedProof } from './types';
import { HttpError } from './types';
export async function consumeRateLimit(env: Env, keyId: string, now = Date.now()): Promise<void> {
  const windowStart = Math.floor(now / 60_000) * 60_000;
  const result = await env.DB.prepare(`INSERT INTO rate_limits(key_id, window_start, accepted_count) VALUES(?, ?, 1)
    ON CONFLICT(key_id, window_start) DO UPDATE SET accepted_count=accepted_count+1 WHERE accepted_count < 100
    RETURNING accepted_count`).bind(keyId, windowStart).first<{accepted_count:number}>();
  if (!result) { const reset = Math.floor((windowStart + 60_000) / 1000); throw new HttpError(429, 'rate limit exceeded', { 'Retry-After': String(Math.max(1, reset - Math.floor(now / 1000))), 'RateLimit-Limit': '100', 'RateLimit-Remaining': '0', 'RateLimit-Reset': String(reset) }); }
}
export async function getProof(env: Env, id: string): Promise<ProofRow | null> {
  return env.DB.prepare('SELECT * FROM verification_batches WHERE verification_id = ?').bind(id).first<ProofRow>();
}
function immutableMatches(row: ProofRow, proof: ValidatedProof): boolean {
  return row.payload_digest === proof.payloadDigest && row.leaf_hash === proof.leaf_hash && row.leaf_index === proof.leaf_index && row.session_id === proof.session_id && row.merkle_root_hash === proof.merkle_root && row.chain === proof.chain;
}
export async function reserveProof(env: Env, proof: ValidatedProof, id: string, r2Key: string, now: number): Promise<{row:ProofRow;created:boolean}> {
  const network = proof.chain === 'base-mainnet' ? '8453' : '84532';
  const result = await env.DB.prepare(`INSERT OR IGNORE INTO verification_batches
    (verification_id,merkle_root_hash,leaf_hash,leaf_index,session_id,payload_digest,r2_key,status,verification_mode,proof_type,proof_version,attestation,chain,network,required_confirmations,created_at,updated_at)
    VALUES(?,?,?,?,?,?,?,'processing','commitment_only','local_merkle_stub','1',0,?,?,?, ?, ?)`).bind(id,proof.merkle_root,proof.leaf_hash,proof.leaf_index,proof.session_id,proof.payloadDigest,r2Key,proof.chain,network,Number(env.CONFIRMATIONS),now,now).run();
  const row = await env.DB.prepare('SELECT * FROM verification_batches WHERE merkle_root_hash = ?').bind(proof.merkle_root).first<ProofRow>();
  if (!row) throw new Error('reservation disappeared');
  if (!immutableMatches(row, proof)) throw new HttpError(409, 'merkle root already exists with conflicting immutable content');
  if (result.meta.changes === 1) {
    await env.DB.prepare(`INSERT INTO proof_leaves(verification_id,leaf_index,leaf_hash,target_domain,path,response_hash,observed_at,metadata_bound)
      VALUES(?,?,?,?,?,?,?,0)`).bind(row.verification_id,proof.leaf_index,proof.leaf_hash,proof.leaf_data.target_domain,proof.leaf_data.path,proof.leaf_data.response_hash,proof.leaf_data.timestamp).run();
  }
  return { row, created: result.meta.changes === 1 };
}
export async function markQueued(env: Env, id: string, now: number): Promise<void> { await env.DB.prepare("UPDATE verification_batches SET status='queued', last_error=NULL, updated_at=? WHERE verification_id=? AND tx_hash IS NULL").bind(now,id).run(); }
export async function markIngestionFailed(env: Env, id: string, error: string, now: number): Promise<void> { await env.DB.prepare("UPDATE verification_batches SET status='failed', last_error=?, updated_at=? WHERE verification_id=? AND tx_hash IS NULL").bind(error.slice(0,512),now,id).run(); }
export function publicProof(row: ProofRow): Record<string, unknown> { return { verification_id: row.verification_id, status: row.status, verification_mode: row.verification_mode, attestation: false, proof_type: row.proof_type, proof_version: row.proof_version, merkle_root: row.merkle_root_hash, payload_digest: row.payload_digest, chain: row.chain, tx_hash: row.tx_hash, confirmations: row.confirmations, required_confirmations: row.required_confirmations, error: row.status === 'failed' ? row.last_error : null, created_at: row.created_at, updated_at: row.updated_at }; }
