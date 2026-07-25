import {readFile} from 'node:fs/promises';import {spawnSync} from 'node:child_process';
const schema=await readFile(new URL('../schema.sql',import.meta.url),'utf8');
const migration=await readFile(new URL('../migrations/0002_anchoring_mode.sql',import.meta.url),'utf8');
const script=String.raw`import sqlite3,sys
schema,migration=sys.stdin.read().split('\0',1)
c=sqlite3.connect(':memory:');c.executescript(schema);c.execute('pragma foreign_keys=on')
required={'idx_batches_owner_id','idx_batches_status_updated','idx_batches_lease','idx_batches_tx_hash','idx_leaves_hash','idx_rate_limits_window'}
assert required <= {r[0] for r in c.execute("select name from sqlite_master where type='index'")}
c.execute("insert into api_keys values(?,?,?,?,?)",('key','0'*32,bytes(32),1,None))
for n in range(100): assert c.execute("insert into rate_limits values('key',0,1) on conflict(key_id,window_start) do update set accepted_count=accepted_count+1 where accepted_count<100 returning accepted_count").fetchone()==(n+1,)
assert c.execute("insert into rate_limits values('key',0,1) on conflict(key_id,window_start) do update set accepted_count=accepted_count+1 where accepted_count<100 returning accepted_count").fetchone() is None
assert c.execute("insert into rate_limits values('key',60000,1) returning accepted_count").fetchone()==(1,)
try:c.execute("insert into rate_limits values('missing',120000,1)");raise AssertionError('foreign key accepted')
except sqlite3.IntegrityError:pass
bad=['0x'+'a'*63+'z','0X'+'a'*64,'0x'+'a'*65]
base=['00000000-0000-4000-8000-000000000000','key','0x'+'a'*64,'0x'+'b'*64,0,'s','0x'+'c'*64,'r2','queued','enabled','commitment_only','local_merkle_stub','1.0.0','1',0,'base-sepolia','84532',3,1000,1000]
columns='verification_id,owner_key_id,merkle_root_hash,leaf_hash,leaf_index,session_id,payload_digest,r2_key,status,anchoring_mode,verification_mode,proof_type,proof_version,envelope_version,attestation,chain,network,required_confirmations,created_at,updated_at'
for i,value in enumerate(bad):
 v=base.copy();v[2]=value;v[0]=f'0000000{i}-0000-4000-8000-000000000000'
 try:c.execute(f"insert into verification_batches({columns}) values({','.join('?'*20)})",v);raise AssertionError('bad hash accepted')
 except sqlite3.IntegrityError:pass
c.commit()
c.execute('begin')
try:
 c.execute(f"insert into verification_batches({columns}) values({','.join('?'*20)})",base)
 c.execute("insert into proof_leaves values(?,?,?,?,?,?,?,?)",(base[0],0,base[3],'EXAMPLE.COM','/?q=1',base[3],1,0))
 c.commit();raise AssertionError('invalid leaf accepted')
except sqlite3.IntegrityError:c.rollback()
assert c.execute('select count(*) from verification_batches').fetchone()==(0,)
stored=base.copy();stored[0]='00000001-0000-4000-8000-000000000000';stored[7]='r2-stored';stored[8]='stored';stored[9]='disabled'
c.execute(f"insert into verification_batches({columns}) values({','.join('?'*20)})",stored)
try:c.execute("update verification_batches set attempts=1 where verification_id=?",(stored[0],));raise AssertionError('stored row consumed an attempt')
except sqlite3.IntegrityError:pass
print('schema ownership, stored-only invariants, strict hashes, timestamps, atomic rollback, foreign keys, indexes, and 100/101 reset verified')`;
const migrationScript=String.raw`import sqlite3,sys
schema,migration=sys.stdin.read().split('\0',1)
old=schema.replace("'stored',",'').replace(",anchoring_mode TEXT NOT NULL CHECK(anchoring_mode IN('enabled','disabled'))",'').replace(",CHECK(status!='stored' OR(anchoring_mode='disabled' AND attempts=0 AND tx_hash IS NULL AND anchor_lease_token IS NULL))",'')
c=sqlite3.connect(':memory:');c.executescript(old);c.execute("insert into api_keys values(?,?,?,?,?)",('key','0'*32,bytes(32),1,None))
base=('00000000-0000-4000-8000-000000000000','key','0x'+'a'*64,'0x'+'b'*64,0,'s','0x'+'c'*64,'r2','queued','commitment_only','local_merkle_stub','1.0.0','1',0,'base-sepolia','84532',3,1000,1000)
columns='verification_id,owner_key_id,merkle_root_hash,leaf_hash,leaf_index,session_id,payload_digest,r2_key,status,verification_mode,proof_type,proof_version,envelope_version,attestation,chain,network,required_confirmations,created_at,updated_at'
c.execute(f"insert into verification_batches({columns}) values({','.join('?'*19)})",base);c.execute("insert into proof_leaves values(?,?,?,?,?,?,?,?)",(base[0],0,base[3],'example.com','/',base[3],1700000000000,0));c.commit();c.executescript(migration)
assert c.execute("select anchoring_mode,status from verification_batches").fetchone()==('enabled','queued')
assert c.execute("select [from],[table] from pragma_foreign_key_list('proof_leaves')").fetchall()==[('verification_id','verification_batches')]
assert c.execute('pragma foreign_key_check').fetchall()==[] and c.execute('select count(*) from proof_leaves').fetchone()==(1,)
print('legacy migration preserves rows, marks them enabled, and retargets leaf foreign keys')`;
for(const source of[script,migrationScript]){const run=spawnSync('python3',['-c',source],{input:`${schema}\0${migration}`,encoding:'utf8'});if(run.status!==0)throw new Error(run.stderr);process.stdout.write(run.stdout)}
