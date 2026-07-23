import { describe,expect,it,vi } from 'vitest'; import { processMessage,retryDelay } from '../src/queue'; import type { AnchorMessage,Env } from '../src/types';
const root=('0x'+'11'.repeat(32)) as `0x${string}`; const digest=('0x'+'22'.repeat(32)) as `0x${string}`; const pointer:AnchorMessage={verification_id:'00000000-0000-4000-8000-000000000000',r2_key:'proofs/x',payload_digest:digest,merkle_root:root,chain:'base-sepolia'};
function message(body:AnchorMessage=pointer,attempts=1){return {body,attempts,ack:vi.fn(),retry:vi.fn()} as unknown as Message<AnchorMessage>;}
describe('queue pointers',()=>{
 it('stays far below 128 KiB and contains no payload',()=>{expect(JSON.stringify(pointer).length).toBeLessThan(512); expect(pointer).not.toHaveProperty('payload');});
 it('bounds exponential backoff',()=>{for(const attempt of [0,1,8,100])expect(retryDelay(attempt)).toBeLessThanOrEqual(43200);});
 it('acks malformed pointers terminally without DB access',async()=>{const msg=message({...pointer,merkle_root:'bad' as `0x${string}`}); const env={} as Env; await processMessage(msg,env); expect(vi.mocked(msg.ack)).toHaveBeenCalledOnce(); expect(vi.mocked(msg.retry)).not.toHaveBeenCalled();});
 it('acks unknown pointer',async()=>{const msg=message(); const env={DB:{prepare:()=>({bind:()=>({first:()=>Promise.resolve(null)})})}} as unknown as Env; await processMessage(msg,env); expect(vi.mocked(msg.ack)).toHaveBeenCalledOnce();});
});
