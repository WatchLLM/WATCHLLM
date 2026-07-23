import { createPublicClient, createWalletClient, encodeFunctionData, fallback, formatGwei, http, keccak256, type Address, type Hash, type Hex } from 'viem';
import { base, baseSepolia } from 'viem/chains';
import { privateKeyToAccount } from 'viem/accounts';
import type { ChainName, Env, ProofRow } from './types';

const anchorAbi = [{ type: 'function', name: 'anchor', stateMutability: 'nonpayable', inputs: [{ name: 'root', type: 'bytes32' }], outputs: [] }] as const;
export class ChainError extends Error { constructor(message: string, public readonly retryable: boolean) { super(message); } }
function config(env: Env, chainName: ChainName) {
  if (env.CHAIN !== chainName) throw new ChainError('configured chain does not match proof chain', false);
  const chain = chainName === 'base-mainnet' ? base : baseSepolia;
  const urls = env.RPC_URLS.split(',').map(value => value.trim()).filter(Boolean);
  if (!urls.length) throw new ChainError('no RPC URLs configured', false);
  const address = env.ANCHOR_CONTRACT_ADDRESS;
  if (!/^0x[0-9a-fA-F]{40}$/.test(address) || /^0x0{40}$/.test(address)) throw new ChainError('anchor contract address is missing or placeholder', false);
  if (!/^0x[0-9a-fA-F]{64}$/.test(env.EVM_PRIVATE_KEY)) throw new ChainError('signing key is not configured', false);
  const transport = fallback(urls.map(url => http(url, { timeout: 10_000, retryCount: 0 })), { retryCount: 0 });
  return { chain, transport, address: address as Address, account: privateKeyToAccount(env.EVM_PRIVATE_KEY as Hex) };
}
export type ChainOutcome = { kind: 'submitted'; hash: Hash; nonce: number } | { kind: 'pending'; confirmations: number } | { kind: 'anchored'; confirmations: number };
export async function anchorOrReconcile(env: Env, row: ProofRow): Promise<ChainOutcome> {
  const { chain, transport, address, account } = config(env, row.chain);
  const publicClient = createPublicClient({ chain, transport });
  if (row.tx_hash) {
    try {
      const receipt = await publicClient.getTransactionReceipt({ hash: row.tx_hash as Hash });
      if (receipt.status === 'reverted') throw new ChainError('anchor transaction reverted', false);
      const head = await publicClient.getBlockNumber();
      const confirmations = Number(head - receipt.blockNumber + 1n);
      return confirmations >= row.required_confirmations ? { kind: 'anchored', confirmations } : { kind: 'pending', confirmations };
    } catch (error) {
      if (error instanceof ChainError) throw error;
      // A pre-persisted hash may be in RPC propagation limbo. Never spend a second nonce blindly.
      throw new ChainError('submitted transaction is not yet available for reconciliation', true);
    }
  }
  const wallet = createWalletClient({ account, chain, transport });
  try {
    const data = encodeFunctionData({ abi: anchorAbi, functionName: 'anchor', args: [row.merkle_root_hash as Hash] });
    const [nonce, gas, fees] = await Promise.all([
      publicClient.getTransactionCount({ address: account.address, blockTag: 'pending' }),
      publicClient.estimateGas({ account: account.address, to: address, data }),
      publicClient.estimateFeesPerGas({ type: 'eip1559' })
    ]);
    const maxFeePerGas = fees.maxFeePerGas; const maxPriorityFeePerGas = fees.maxPriorityFeePerGas;
    if (maxFeePerGas > BigInt(env.MAX_FEE_PER_GAS_WEI) || maxPriorityFeePerGas > BigInt(env.MAX_PRIORITY_FEE_PER_GAS_WEI) || gas * maxFeePerGas > BigInt(env.MAX_TOTAL_FEE_WEI)) {
      throw new ChainError(`gas policy deferred transaction (maxFee=${formatGwei(maxFeePerGas)} gwei)`, true);
    }
    const request = { chainId: chain.id, to: address, data, nonce, gas, maxFeePerGas, maxPriorityFeePerGas, type: 'eip1559' as const };
    const serialized = await account.signTransaction(request);
    const hash = keccak256(serialized);
    // Persisting hash/nonce before broadcast is performed by queue.ts via prepare callback boundary.
    await env.DB.prepare("UPDATE verification_batches SET status='submitted', tx_hash=?, tx_nonce=?, submitted_at=COALESCE(submitted_at,?), updated_at=? WHERE verification_id=? AND tx_hash IS NULL")
      .bind(hash, nonce, Date.now(), Date.now(), row.verification_id).run();
    try { await wallet.sendRawTransaction({ serializedTransaction: serialized }); }
    catch { throw new ChainError('transaction broadcast uncertain; reconcile persisted hash before any replacement', true); }
    return { kind: 'submitted', hash, nonce };
  } catch (error) {
    if (error instanceof ChainError) throw error;
    throw new ChainError('RPC or signing operation failed', true);
  }
}
