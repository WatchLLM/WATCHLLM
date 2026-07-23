import { anchorOrReconcile, ChainError } from './chain';
import { getProof } from './db';
import type { AnchorMessage, Env } from './types';
const MAX_DELAY_SECONDS = 43_200;
export function retryDelay(attempts: number): number { const base = Math.min(MAX_DELAY_SECONDS, 15 * 2 ** Math.min(attempts, 11)); return Math.min(MAX_DELAY_SECONDS, base + Math.floor(Math.random() * Math.max(1, base / 4))); }
function validPointer(message: AnchorMessage): boolean { return JSON.stringify(message).length < 131_072 && /^0x[0-9a-f]{64}$/.test(message.merkle_root) && /^0x[0-9a-f]{64}$/.test(message.payload_digest) && !('payload' in message); }
export async function processMessage(message: Message<AnchorMessage>, env: Env): Promise<void> {
  if (!validPointer(message.body)) { message.ack(); return; }
  const row = await getProof(env, message.body.verification_id);
  if (!row || row.r2_key !== message.body.r2_key || row.payload_digest !== message.body.payload_digest || row.merkle_root_hash !== message.body.merkle_root || row.chain !== message.body.chain) { message.ack(); return; }
  if (row.status === 'anchored' || (row.status === 'failed' && row.tx_hash === null)) { message.ack(); return; }
  const attempt = message.attempts;
  await env.DB.prepare("UPDATE verification_batches SET status=CASE WHEN tx_hash IS NULL THEN 'processing' ELSE 'submitted' END, attempts=attempts+1, updated_at=? WHERE verification_id=?").bind(Date.now(),row.verification_id).run();
  try {
    const outcome = await anchorOrReconcile(env, row);
    if (outcome.kind === 'anchored') {
      await env.DB.prepare("UPDATE verification_batches SET status='anchored', confirmations=?, anchored_at=?, updated_at=?, last_error=NULL WHERE verification_id=?").bind(outcome.confirmations,Date.now(),Date.now(),row.verification_id).run(); message.ack(); return;
    }
    if (outcome.kind === 'pending') await env.DB.prepare("UPDATE verification_batches SET status='submitted', confirmations=?, updated_at=? WHERE verification_id=?").bind(outcome.confirmations,Date.now(),row.verification_id).run();
    message.retry({ delaySeconds: retryDelay(attempt) });
  } catch (error) {
    const chainError = error instanceof ChainError ? error : new ChainError('internal anchoring failure', true);
    const max = Number(env.MAX_ATTEMPTS);
    if (!chainError.retryable || attempt >= max) {
      await env.DB.prepare("UPDATE verification_batches SET status='failed', last_error=?, updated_at=? WHERE verification_id=?").bind(chainError.message.slice(0,512),Date.now(),row.verification_id).run(); message.ack(); return;
    }
    await env.DB.prepare("UPDATE verification_batches SET status=CASE WHEN tx_hash IS NULL THEN 'queued' ELSE 'submitted' END, last_error=?, updated_at=? WHERE verification_id=?").bind(chainError.message.slice(0,512),Date.now(),row.verification_id).run();
    message.retry({ delaySeconds: retryDelay(attempt) });
  }
}
export async function consume(batch: MessageBatch<AnchorMessage>, env: Env): Promise<void> { await Promise.all(batch.messages.map(message => processMessage(message, env))); }
