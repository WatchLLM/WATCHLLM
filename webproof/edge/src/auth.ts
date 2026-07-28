import type { Env } from './types';
import { HttpError } from './types';
const encoder = new TextEncoder();
export function constantTimeEqual(a: Uint8Array, b: Uint8Array): boolean {
  const length = Math.max(a.length, b.length); let difference = a.length ^ b.length;
  for (let index = 0; index < length; index++) difference |= (a[index] ?? 0) ^ (b[index] ?? 0);
  return difference === 0;
}
export async function keyDigest(pepper: string, salt: string, secret: string): Promise<Uint8Array> {
  const key = await crypto.subtle.importKey('raw', encoder.encode(pepper), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(`${salt}\0${secret}`)));
}
function parseBearer(request: Request): { keyId: string; secret: string } {
  const authorization = request.headers.get('authorization');
  if (!authorization?.startsWith('Bearer ') || authorization.includes(',')) throw new HttpError(401, 'unauthorized', { 'WWW-Authenticate': 'Bearer' });
  const token = authorization.slice(7); const separator = token.indexOf('.');
  if (separator < 1 || separator === token.length - 1 || token.length > 512) throw new HttpError(401, 'unauthorized', { 'WWW-Authenticate': 'Bearer' });
  const keyId = token.slice(0, separator); const secret = token.slice(separator + 1);
  if (!/^[A-Za-z0-9_-]{1,64}$/.test(keyId) || secret.length > 447 || /\s/.test(secret)) throw new HttpError(401, 'unauthorized', { 'WWW-Authenticate': 'Bearer' });
  return { keyId, secret };
}
export async function authenticate(request: Request, env: Env): Promise<string> {
  const { keyId, secret } = parseBearer(request);
  const row = await env.DB.prepare('SELECT key_id, salt, digest FROM api_keys WHERE key_id = ? AND disabled_at IS NULL').bind(keyId).first<{key_id:string;salt:string;digest:ArrayBuffer}>();
  const salt = row?.salt ?? '00000000000000000000000000000000';
  const expected = row ? new Uint8Array(row.digest) : new Uint8Array(32);
  const actual = await keyDigest(env.API_KEY_PEPPER, salt, secret);
  if (!row || !constantTimeEqual(actual, expected)) throw new HttpError(401, 'unauthorized', { 'WWW-Authenticate': 'Bearer' });
  return row.key_id;
}
