import { authenticate } from './auth';
import { consumeRateLimit, getProof, markIngestionFailed, markQueued, markStored, publicProof, reserveProof } from './db';
import { consume } from './queue';
import { loadConfig } from './config';
import { HttpError, MAX_DECODED_BYTES, MAX_ENVELOPE_BYTES, NODE_DOMAIN, type AnchorMessage, type Env, type ProofEnvelope, type ValidatedProof } from './types';
const encoder = new TextEncoder();
function json(value: unknown, status = 200, headers: HeadersInit = {}): Response { return Response.json(value, { status, headers: new Headers({ 'Cache-Control': 'no-store', ...(headers as Record<string,string>) }) }); }
function normalizeHash(value: unknown, field: string): `0x${string}` { if (typeof value !== 'string') throw new HttpError(400, `${field} must be a 32-byte hex string`); const normalized = value.startsWith('0x') ? value : `0x${value}`; if (!/^0x[0-9a-fA-F]{64}$/.test(normalized)) throw new HttpError(400, `${field} must be a 32-byte hex string`); return normalized.toLowerCase() as `0x${string}`; }
function decodeBase64(value: unknown): Uint8Array {
  if (typeof value !== 'string' || value.length === 0 || value.length % 4 !== 0 || !/^(?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?$/.test(value)) throw new HttpError(400, 'proof_payload must be strict padded base64');
  const padding = value.endsWith('==') ? 2 : value.endsWith('=') ? 1 : 0; const size = value.length / 4 * 3 - padding;
  if (size > MAX_DECODED_BYTES) throw new HttpError(413, 'decoded proof payload exceeds 1 MiB');
  const binary = atob(value); const bytes = Uint8Array.from(binary, character => character.charCodeAt(0));
  let canonical = ''; for (let offset=0; offset<bytes.length; offset+=0x8000) canonical += String.fromCharCode(...bytes.subarray(offset,offset+0x8000));
  if (btoa(canonical) !== value) throw new HttpError(400, 'proof_payload is not canonical base64');
  return bytes;
}
async function sha256Hex(bytes: Uint8Array): Promise<`0x${string}`> { return `0x${Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength) as ArrayBuffer))).map(byte => byte.toString(16).padStart(2,'0')).join('')}`; }
async function nodeHash(left: `0x${string}`, right: `0x${string}`): Promise<`0x${string}`> { const pair = new Uint8Array(NODE_DOMAIN.length + 64); pair.set(NODE_DOMAIN); pair.set(Uint8Array.from(left.slice(2).match(/../g) ?? [], byte => Number.parseInt(byte,16)),NODE_DOMAIN.length); pair.set(Uint8Array.from(right.slice(2).match(/../g) ?? [], byte => Number.parseInt(byte,16)),NODE_DOMAIN.length+32); return sha256Hex(pair); }
async function validateEnvelope(raw: unknown, env: Env): Promise<ValidatedProof> {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) throw new HttpError(400,'request body must be an object');
  const value = raw as Partial<ProofEnvelope>;
  const allowed = new Set(['envelope_version','proof_version','proof_type','verification_mode','attestation','merkle_root','leaf_hash','leaf_index','merkle_path','session_id','leaf_data','proof_payload','chain']);
  for (const key of Object.keys(value)) if (!allowed.has(key)) throw new HttpError(400,`unsupported field: ${key}`);
  if (value.envelope_version !== '1' || value.proof_version !== '1.0.0' || value.proof_type !== 'local_merkle_stub' || value.verification_mode !== 'commitment_only' || value.attestation !== false) throw new HttpError(400,'only envelope 1 / proof 1.0.0 local_merkle_stub commitment_only with attestation=false is supported');
  const merkle_root = normalizeHash(value.merkle_root,'merkle_root'); const leaf_hash = normalizeHash(value.leaf_hash,'leaf_hash');
  if (!Number.isSafeInteger(value.leaf_index) || (value.leaf_index ?? -1) < 0) throw new HttpError(400,'leaf_index must be a nonnegative safe integer');
  if (!Array.isArray(value.merkle_path) || value.merkle_path.length > 64) throw new HttpError(400,'merkle_path must contain at most 64 hashes');
  const merkle_path = value.merkle_path.map((hash,index) => normalizeHash(hash,`merkle_path[${String(index)}]`));
  if (typeof value.session_id !== 'string' || encoder.encode(value.session_id).length === 0 || encoder.encode(value.session_id).length > 64) throw new HttpError(400,'session_id must be 1-64 UTF-8 bytes');
  const metadata = value.leaf_data;
  if (!metadata || typeof metadata !== 'object' || Object.keys(metadata).some(key => !['target_domain','path','response_hash','timestamp'].includes(key))) throw new HttpError(400,'invalid leaf_data');
  if (typeof metadata.target_domain !== 'string' || encoder.encode(metadata.target_domain).length > 253 || metadata.target_domain !== metadata.target_domain.toLowerCase() || !/^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)*[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?$/.test(metadata.target_domain)) throw new HttpError(400,'target_domain must be a DNS hostname');
  if (typeof metadata.path !== 'string' || !metadata.path.startsWith('/') || metadata.path.includes('?') || metadata.path.includes('#') || metadata.path.length > 2048) throw new HttpError(400,'path must be an absolute path without query or fragment');
  const response_hash = normalizeHash(metadata.response_hash,'response_hash');
  const now = Date.now(); if (!Number.isSafeInteger(metadata.timestamp) || metadata.timestamp < 946684800000 || metadata.timestamp > now + 300000) throw new HttpError(400,'timestamp is outside the plausible millisecond range');
  const payload = decodeBase64(value.proof_payload); const payloadDigest = await sha256Hex(payload);
  let computed = leaf_hash; let index = value.leaf_index as number;
  for (const sibling of merkle_path) { computed = (index & 1) === 0 ? await nodeHash(computed,sibling) : await nodeHash(sibling,computed); index = Math.floor(index/2); }
  if (computed !== merkle_root) throw new HttpError(400,'merkle inclusion path does not match root');
  const chain = value.chain ?? (env.CHAIN === 'base-mainnet' ? 'base-mainnet' : 'base-sepolia');
  return { envelope_version:'1',proof_version:'1.0.0',proof_type:'local_merkle_stub',verification_mode:'commitment_only',attestation:false,merkle_root,leaf_hash,leaf_index:value.leaf_index as number,merkle_path,session_id:value.session_id,leaf_data:{...metadata,target_domain:metadata.target_domain.toLowerCase(),response_hash},payload,payloadDigest,chain };
}
async function readJson(request: Request): Promise<unknown> { const declared = Number(request.headers.get('content-length')); if (Number.isFinite(declared) && declared > MAX_ENVELOPE_BYTES) throw new HttpError(413,'request envelope exceeds 1.5 MiB'); const bytes = new Uint8Array(await request.arrayBuffer()); if (bytes.byteLength > MAX_ENVELOPE_BYTES) throw new HttpError(413,'request envelope exceeds 1.5 MiB'); try { return JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)); } catch { throw new HttpError(400,'body must be valid UTF-8 JSON'); } }
async function postProof(request: Request, env: Env): Promise<Response> {
  const config=loadConfig(env);
  const raw=await readJson(request); const keyId = await authenticate(request,env); const proof = await validateEnvelope(raw,env); await consumeRateLimit(env,keyId);
  const id = crypto.randomUUID(); const r2Key = `proofs/${id}/${proof.payloadDigest.slice(2)}`; const now = Date.now(); const reservation = await reserveProof(env,proof,keyId,id,r2Key,now);
  if (!reservation.created && ['stored','queued','submitted','anchored'].includes(reservation.row.status)) return json(publicProof(reservation.row),202);
  const repairingDisabled = !reservation.created && reservation.row.status === 'processing' && config.anchoringMode === 'disabled' && reservation.row.anchoring_mode === 'disabled';
  if (!reservation.created && reservation.row.status === 'processing' && !repairingDisabled) throw new HttpError(503,'matching ingestion is still in progress',{ 'Retry-After':'1' });
  const targetId = reservation.row.verification_id; const targetKey = reservation.row.r2_key;
  try { await env.PROOFS.put(targetKey,proof.payload,{httpMetadata:{contentType:'application/octet-stream'},customMetadata:{digest:proof.payloadDigest}}); }
  catch { if (!repairingDisabled) await markIngestionFailed(env,targetId,'proof object storage failed',Date.now()); throw new HttpError(503,'durable proof storage unavailable'); }
  if (config.anchoringMode === 'disabled') {
    try {
      const changed=await markStored(env,targetId,Date.now());
      const row=await getProof(env,targetId,keyId);
      if (row?.status === 'stored' && row.anchoring_mode === 'disabled') return json(publicProof(row),202);
      if (!changed || !row) throw new HttpError(503,'durable stored-only state unavailable');
    } catch(error) { if(error instanceof HttpError)throw error; throw new HttpError(503,'durable stored-only state unavailable'); }
    throw new HttpError(503,'durable stored-only state unavailable');
  }
  const pointer: AnchorMessage = {verification_id:targetId,r2_key:targetKey,payload_digest:proof.payloadDigest,merkle_root:proof.merkle_root,chain:proof.chain};
  try { await env.ANCHOR_QUEUE.send(pointer); }
  catch { try { await env.PROOFS.delete(targetKey); } catch { /* orphan lifecycle cleanup is documented */ } await markIngestionFailed(env,targetId,'queue handoff failed; retry submission',Date.now()); throw new HttpError(503,'durable queue handoff unavailable'); }
  try { await markQueued(env,targetId,Date.now()); } catch { /* handoff is durable; consumer and retry converge from processing */ }
  const row = await getProof(env,targetId,keyId); if (!row) throw new Error('proof missing after queue handoff');
  if (row.status === 'processing') return json({...publicProof(row),status:'queued'},202);
  return json(publicProof(row),202);
}
async function fetchHandler(request:Request,env:Env):Promise<Response>{try{loadConfig(env);const url=new URL(request.url);if(url.pathname==='/proof'){if(request.method!=='POST')return json({error:'method not allowed'},405,{Allow:'POST'});const declared=request.headers.get('content-length');if(declared!==null&&/^[0-9]+$/.test(declared)&&Number(declared)>MAX_ENVELOPE_BYTES)throw new HttpError(413,'request envelope exceeds 1.5 MiB');return await postProof(request,env)}const match=/^\/proof\/([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})$/.exec(url.pathname);if(match){if(request.method!=='GET')return json({error:'method not allowed'},405,{Allow:'GET'});const keyId=await authenticate(request,env);const row=await getProof(env,match[1]??'',keyId);return row?json(publicProof(row)):json({error:'not found'},404)}return json({error:'not found'},404)}catch(error){if(error instanceof HttpError)return json({error:error.message},error.status,error.headers);console.error('webproof edge request failed');return json({error:'internal error'},500)}}
export { validateEnvelope, decodeBase64, normalizeHash, fetchHandler };
export default { fetch: fetchHandler, queue: consume } satisfies ExportedHandler<Env, AnchorMessage>;
