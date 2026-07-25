import { describe, expect, it } from 'vitest';
import { decodeBase64, fetchHandler, normalizeHash, validateEnvelope } from '../src/index';
import { constantTimeEqual, keyDigest } from '../src/auth';
import { MAX_DECODED_BYTES, type Env } from '../src/types';
const hex='0x'+'11'.repeat(32); const baseEnv={ANCHORING_MODE:'enabled',CHAIN:'base-sepolia',CONFIRMATIONS:'3',MAX_ATTEMPTS:'8',MAX_EXECUTION_FEE_WEI:'2000000000000000',MAX_FEE_PER_GAS_WEI:'50000000000',MAX_PRIORITY_FEE_PER_GAS_WEI:'5000000000',ANCHOR_LEASE_MS:'120000'} as Env;
function envelope(overrides:Record<string,unknown>={}) { return {envelope_version:'1',proof_version:'1.0.0',proof_type:'local_merkle_stub',verification_mode:'commitment_only',attestation:false,merkle_root:hex,leaf_hash:hex,leaf_index:0,merkle_path:[],session_id:'session',leaf_data:{target_domain:'example.com',path:'/private/path',response_hash:'22'.repeat(32),timestamp:Date.now()},proof_payload:'aGk=',...overrides}; }
describe('strict commitment envelope',()=>{
 it('normalizes roots and accepts a valid leaf-to-root commitment',async()=>{expect(normalizeHash('AA'.repeat(32),'root')).toBe('0x'+'aa'.repeat(32)); const value=await validateEnvelope(envelope(),baseEnv); expect(value.verification_mode).toBe('commitment_only'); expect(value.attestation).toBe(false); expect(value.payloadDigest).toMatch(/^0x[0-9a-f]{64}$/);});
 it.each(['abc','a===','!!!!','aGk'])('rejects malformed base64 %s',(value)=>expect(()=>decodeBase64(value)).toThrow(/base64/));
 it('enforces decoded size',()=>{const oversized='A'.repeat(Math.ceil((MAX_DECODED_BYTES+1)/3)*4); expect(()=>decodeBase64(oversized)).toThrow(/1 MiB/);});
 it.each([
  {verification_mode:'verified'}, {attestation:true}, {proof_type:'remote'}, {proof_version:'2.0.0'}, {leaf_index:-1}, {merkle_path:Array(65).fill(hex)},
  {leaf_data:{target_domain:'https://example.com?q=x',path:'/',response_hash:hex,timestamp:Date.now()}},
  {leaf_data:{target_domain:'example.com',path:'/x?secret=1',response_hash:hex,timestamp:Date.now()}},
  {leaf_data:{target_domain:'example.com',path:'/x#frag',response_hash:hex,timestamp:Date.now()}}
 ])('fails closed for unsupported/privacy-unsafe input %#',async(overrides)=>await expect(validateEnvelope(envelope(overrides),baseEnv)).rejects.toBeTruthy());
 it('rejects invalid inclusion path',async()=>await expect(validateEnvelope(envelope({merkle_path:['0x'+'33'.repeat(32)]}),baseEnv)).rejects.toThrow(/inclusion/));
 it('canonicalizes only lowercase ASCII domains and validates UUID routes',async()=>{const upper=envelope({leaf_data:{target_domain:'Example.COM',path:'/',response_hash:hex,timestamp:Date.now()}});await expect(validateEnvelope(upper,baseEnv)).rejects.toThrow(/hostname/);const unicode=envelope({leaf_data:{target_domain:'éxample.com',path:'/',response_hash:hex,timestamp:Date.now()}});await expect(validateEnvelope(unicode,baseEnv)).rejects.toThrow(/hostname/);const response=await fetchHandler(new Request('https://edge.test/proof/not-a-uuid'),baseEnv);expect(response.status).toBe(404);});
 it('rejects unknown fields',async()=>await expect(validateEnvelope(envelope({url:'https://example.com/?secret'}),baseEnv)).rejects.toThrow(/unsupported field/));
});
describe('authentication primitives',()=>{
 it('compares equal and unequal lengths without prefix acceptance',()=>{expect(constantTimeEqual(new Uint8Array([1,2]),new Uint8Array([1,2]))).toBe(true); expect(constantTimeEqual(new Uint8Array([1]),new Uint8Array([1,0]))).toBe(false);});
 it('uses pepper, salt, and secret in API-key digest',async()=>{const a=await keyDigest('pepper','0'.repeat(32),'secret'); expect(a).toHaveLength(32); expect(a).not.toEqual(await keyDigest('pepper','1'.repeat(32),'secret')); expect(a).not.toEqual(await keyDigest('pepper','0'.repeat(32),'other'));});
});
describe('routing',()=>{
 it('returns method and route contracts without touching payloads',async()=>{const env=baseEnv; let response=await fetchHandler(new Request('https://edge.test/proof',{method:'GET'}),env); expect(response.status).toBe(405); expect(response.headers.get('allow')).toBe('POST'); response=await fetchHandler(new Request('https://edge.test/missing'),env); expect(response.status).toBe(404);});
 it('fast rejects oversized content length after auth path is unavailable',async()=>{const env={...baseEnv,DB:{prepare:()=>({bind:()=>({first:()=>Promise.resolve(null)})})},API_KEY_PEPPER:'pepper'} as unknown as Env; const response=await fetchHandler(new Request('https://edge.test/proof',{method:'POST',headers:{authorization:'Bearer id.secret','content-length':'2000000'},body:'{}'}),env); expect(response.status).toBe(413); expect(await response.text()).not.toContain('secret');});
});
