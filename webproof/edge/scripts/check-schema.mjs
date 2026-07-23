import {readFile} from 'node:fs/promises'; import {spawnSync} from 'node:child_process';
const schema=await readFile(new URL('../schema.sql',import.meta.url),'utf8');
const script=String.raw`import sqlite3,sys
c=sqlite3.connect(':memory:'); c.executescript(sys.stdin.read()); c.execute('pragma foreign_keys=on')
assert c.execute("select count(*) from sqlite_master where type='index' and name in ('idx_batches_status_updated','idx_batches_tx_hash','idx_leaves_hash','idx_rate_limits_window')").fetchone()[0]==4
c.execute("insert into api_keys values(?,?,?,?,?)",('key','0'*32,bytes(32),1,None))
for n in range(100): c.execute("insert into rate_limits values('key',0,1) on conflict(key_id,window_start) do update set accepted_count=accepted_count+1 where accepted_count<100 returning accepted_count").fetchone()
assert c.execute("insert into rate_limits values('key',0,1) on conflict(key_id,window_start) do update set accepted_count=accepted_count+1 where accepted_count<100 returning accepted_count").fetchone() is None
assert c.execute("insert into rate_limits values('key',60000,1) on conflict(key_id,window_start) do update set accepted_count=accepted_count+1 where accepted_count<100 returning accepted_count").fetchone()==(1,)
try: c.execute("insert into rate_limits values('missing',0,1)"); raise AssertionError('foreign key accepted')
except sqlite3.IntegrityError: pass
try: c.execute("insert into verification_batches(verification_id,merkle_root_hash,leaf_hash,leaf_index,session_id,payload_digest,r2_key,status,verification_mode,proof_type,proof_version,attestation,chain,network,required_confirmations,created_at,updated_at) values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('x'*36,'bad','bad',-1,'','bad','x','verified','verified','remote','2',1,'other','1',0,2,1)); raise AssertionError('constraints accepted')
except sqlite3.IntegrityError: pass
print('schema, constraints, foreign keys, indexes, and 100/101 window reset verified')`;
const run=spawnSync('python3',['-c',script],{input:schema,encoding:'utf8'}); if(run.status!==0)throw new Error(run.stderr); process.stdout.write(run.stdout);
