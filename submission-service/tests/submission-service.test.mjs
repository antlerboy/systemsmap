import {DatabaseSync} from 'node:sqlite';
import {readFileSync,readdirSync} from 'node:fs';
import assert from 'node:assert/strict';
import worker from '../redirect-worker.mjs';
import {validate} from '../submission-worker.mjs';
const sql=new DatabaseSync(':memory:');
for(const f of readdirSync('drizzle').filter(f=>f.endsWith('.sql')))sql.exec(readFileSync('drizzle/'+f,'utf8'));
const env={DB:{prepare(query){
 const statement=sql.prepare(query);let values=[];
 return {
  bind(...v){values=v;return this;},
  async first(){return statement.get(...values)||null;},
  async all(){return {results:statement.all(...values)};},
  async run(){return {meta:{changes:Number(statement.run(...values).changes)}};}
 };
}}};
const origin='https://transduction.systems';
function request(body,options={}){return new Request('https://events.transduction.systems/api/submissions',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json','CF-Connecting-IP':'203.0.113.20',...options.headers},body:JSON.stringify(body)});}
const r=await worker.fetch(request({url:'https://example.org/event'}),env);assert.equal(r.status,201);const receipt=await r.json();assert.equal(receipt.received,true);assert(receipt.id);
assert.equal(r.headers.get('Access-Control-Allow-Origin'),origin);
const reread=await worker.fetch(new Request('https://events.transduction.systems/api/submissions'),env);const saved=(await reread.json()).submissions;assert.equal(saved.length,1);assert.equal(saved[0].url,'https://example.org/event');assert(!JSON.stringify(saved).includes('daily_client'));assert(!JSON.stringify(saved).includes('203.0.113.20'));
const duplicate=await worker.fetch(request({url:'https://example.org/event'}),env);assert.equal(duplicate.status,200);assert.equal((await duplicate.json()).id,receipt.id);
assert.equal((await worker.fetch(request({url:'https://example.org/bot',website:'spam'}),env)).status,400);
assert.equal((await worker.fetch(request({url:'https://example.org/other'},{headers:{Origin:'https://unrelated.example'}}),env)).status,403);
assert.throws(()=>validate({url:'http://127.0.0.1/private'}));assert.throws(()=>validate({url:'https://user:password@example.org'}));
for(let i=1;i<10;i++)assert.equal((await worker.fetch(request({url:'https://example.org/'+i}),env)).status,201);
assert.equal((await worker.fetch(request({url:'https://example.org/over-limit'}),env)).status,429);
assert.equal((await worker.fetch(new Request('https://events.transduction.systems/api/submissions',{method:'OPTIONS',headers:{Origin:origin}}),env)).status,204);
const down=await worker.fetch(request({url:'https://example.org/down'}),{});assert.equal(down.status,503);assert.equal((await down.json()).received,undefined);
for(const [url,target] of [['https://events.transduction.systems/?q=Poland','https://transduction.systems/events/?q=Poland'],['https://publicservicetransformation.com/old-page','https://www.publicservicetransformation.org/'],['https://publicservicetransformation.com/api/submissions','https://www.publicservicetransformation.org/']]){
 const r=await worker.fetch(new Request(url),env);assert.equal(r.status,301);assert.equal(r.headers.get('Location'),target);
}
console.log('Verified anonymous durable receipt, CORS, duplicate handling, rate limits, errors, and existing redirects.');
