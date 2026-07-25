import { describe, expect, it } from 'vitest';
import fixtureData from './fixtures/python-envelope-v1.json';
import { validateEnvelope } from '../src/index';
import type { Env } from '../src/types';

const fixture: Record<string, unknown> = { ...fixtureData };
delete fixture['_python_records'];
const env = { CHAIN: 'base-sepolia' } as Env;

describe('Python SDK to Edge contract', () => {
  it('accepts an envelope generated from native Python records and proof', async () => {
    const validated = await validateEnvelope(fixture, env);
    expect(validated.merkle_root).toBe(`0x${String(fixture['merkle_root']).replace(/^0x/, '')}`);
    expect(validated.leaf_hash).toBe(`0x${String(fixture['leaf_hash']).replace(/^0x/, '')}`);
    expect(validated.leaf_index).toBe(2);
    expect(validated.merkle_path).toHaveLength(2);
    expect(new TextDecoder().decode(validated.payload)).toContain('"leaf_count":3');
  });
});
