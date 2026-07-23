import {readFile} from 'node:fs/promises';import {spawnSync} from 'node:child_process';
const schema=await readFile(new URL('../schema.sql',import.meta.url),'utf8');
const script=String.raw`import sqlite3,sys
c=sqlite3.connect(':memory:');c.executescript(sys.stdin.read());c.execute('pragma foreign_keys=on')
required={'idx_batches_owner_id','idx_batches_status_updated','idx_batches_lease','idx_batches_tx_hash','idx_leaves_hash','idx_rate_limits_window'}
assert required <= {r[0] for r in c.execute("select name from sqlite_master where type='index'")}
c.execute("insert into api_keys values(?,?,?,?,?)",('key','0'*32,bytes(32),1,None))
for n in range(100): assert c.execute("insert into rate_limits values('key',0,1) on conflict(key_id,window_start) do update set accepted_count=accepted_count+1 where accepted_count<100 returning accepted_count").fetchone()==(n+1,)
assert c.execute("insert into rate_limits values('key',0,1) on conflict(key_id,window_start) do update set accepted_count=accepted_count+1 where accepted_count<100 returning accepted_count").fetchone() is None
assert c.execute("insert into rate_limits values('key',60000,1) returning accepted_count").fetchone()==(1,)
try:c.execute("insert into rate_limits values('missing',120000,1)");raise AssertionError('foreign key accepted')
except sqlite3.IntegrityError:pass
bad=['0x'+'a'*63+'z','0X'+'a'*64,'0x'+'a'*65]
base=['00000000-0000-4000-8000-000000000000','key','0x'+'a'*64,'0x'+'b'*64,0,'s','0x'+'c'*64,'r2','queued','commitment_only','local_merkle_stub','1.0.0','1',0,'base-sepolia','84532',3,1000,1000]
columns='verification_id,owner_key_id,merkle_root_hash,leaf_hash,leaf_index,session_id,payload_digest,r2_key,status,verification_mode,proof_type,proof_version,envelope_version,attestation,chain,network,required_confirmations,created_at,updated_at'
for i,value in enumerate(bad):
 v=base.copy();v[2]=value;v[0]=f'0000000{i}-0000-4000-8000-000000000000'
 try:c.execute(f"insert into verification_batches({columns}) values({','.join('?'*19)})",v);raise AssertionError('bad hash accepted')
 except sqlite3.IntegrityError:pass
c.commit()
c.execute('begin')
try:
 c.execute(f"insert into verification_batches({columns}) values({','.join('?'*19)})",base)
 c.execute("insert into proof_leaves values(?,?,?,?,?,?,?,?)",(base[0],0,base[3],'EXAMPLE.COM','/?q=1',base[3],1,0))
 c.commit();raise AssertionError('invalid leaf accepted')
except sqlite3.IntegrityError:c.rollback()
assert c.execute('select count(*) from verification_batches').fetchone()==(0,)
print('schema ownership, strict hashes, timestamps, atomic rollback, foreign keys, indexes, and 100/101 reset verified')`;
const run=spawnSync('python3',['-c',script],{input:schema,encoding:'utf8'});if(run.status!==0)throw new Error(run.stderr);process.stdout.write(run.stdout);
