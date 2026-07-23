export const MAX_DECODED_BYTES = 1_048_576;
export const MAX_ENVELOPE_BYTES = 1_572_864;
export const NODE_DOMAIN = new TextEncoder().encode('watchllm-webproof-local-node-v1\0');
export type ProofStatus = 'queued' | 'processing' | 'submitted' | 'anchored' | 'failed';
export type VerificationMode = 'commitment_only';
export type ChainName = 'base-sepolia' | 'base-mainnet';
export interface Env {
  DB: D1Database; PROOFS: R2Bucket; ANCHOR_QUEUE: Queue<AnchorMessage>;
  API_KEY_PEPPER: string; EVM_PRIVATE_KEY: string; CHAIN: string; RPC_URLS: string;
  ANCHOR_CONTRACT_ADDRESS: string; CONFIRMATIONS: string; MAX_ATTEMPTS: string;
  MAX_TOTAL_FEE_WEI: string; MAX_FEE_PER_GAS_WEI: string; MAX_PRIORITY_FEE_PER_GAS_WEI: string;
}
export interface LeafMetadata { target_domain: string; path: string; response_hash: string; timestamp: number }
export interface ProofEnvelope {
  proof_version: '1'; proof_type: 'local_merkle_stub'; verification_mode: 'commitment_only'; attestation: false;
  merkle_root: string; leaf_hash: string; leaf_index: number; merkle_path: string[];
  session_id: string; leaf_data: LeafMetadata; proof_payload: string; chain?: ChainName;
}
export interface ValidatedProof extends Omit<ProofEnvelope, 'proof_payload' | 'chain'> {
  payload: Uint8Array; payloadDigest: string; merkle_root: `0x${string}`; leaf_hash: `0x${string}`;
  merkle_path: `0x${string}`[]; chain: ChainName;
}
export interface AnchorMessage { verification_id: string; r2_key: string; payload_digest: string; merkle_root: `0x${string}`; chain: ChainName }
export interface ProofRow {
  verification_id: string; merkle_root_hash: string; leaf_hash: string; leaf_index: number; session_id: string;
  payload_digest: string; r2_key: string; status: ProofStatus; verification_mode: VerificationMode; proof_type: string;
  proof_version: string; attestation: number; chain: ChainName; network: string; attempts: number; last_error: string | null;
  tx_hash: string | null; tx_nonce: number | null; confirmations: number; required_confirmations: number;
  created_at: number; updated_at: number; submitted_at: number | null; anchored_at: number | null;
}
export class HttpError extends Error { constructor(public readonly status: number, message: string, public readonly headers: HeadersInit = {}) { super(message); } }
