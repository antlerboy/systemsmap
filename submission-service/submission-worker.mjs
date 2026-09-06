const allowedOrigins=new Set(['https://transduction.systems','https://events.transduction.systems','https://antlerboy.github.io','https://systems-events-map.redquadrant-0856.chatgpt.site']);
const limits={title:180,organiser:120,description:600,location:300,timezone:80,language:120,languageRequirement:300,interpretation:300,access:300,start:10,end:10,startTime:5,endTime:5};
const db=env=>{if(!env.DB)throw Error('Submission storage unavailable');return env.DB;};
function cors(origin){return {'Access-Control-Allow-Origin':origin||'*','Access-Control-Allow-Methods':'GET, POST, OPTIONS','Access-Control-Allow-Headers':'Content-Type','Vary':'Origin'};}
function json(data,status=200,origin=''){return new Response(JSON.stringify(data),{status,headers:{...cors(origin),'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
export function validate(input){
 if(!input||typeof input!=='object'||Array.isArray(input))throw Error('Please paste a public link.');
 if(input.website)throw Error('Submission could not be accepted.');
 if(typeof input.url!=='string'||input.url.length>1200)throw Error('Please paste a public link.');
 const u=new URL(input.url.trim().replace(/^webcal:/i,'https:'));
 if(!['http:','https:'].includes(u.protocol)||u.username||u.password||u.port&&!['80','443'].includes(u.port)||!u.hostname.includes('.')||/^(?:localhost|127\.|10\.|0\.|169\.254\.|192\.168\.|172\.(?:1[6-9]|2\d|3[01])\.)/i.test(u.hostname)||/\.(?:local|internal|localhost)$/i.test(u.hostname))throw Error('Use a public https:// or webcal:// link.');
 u.hash='';const data={kind:['event','feed','page'].includes(input.kind)?input.kind:'auto',url:u.href};
 for(const [key,max] of Object.entries(limits)){
  if(input[key]!=null&&input[key]!==''){
   if(typeof input[key]!=='string'||input[key].length>max)throw Error('Please shorten or correct '+key+'.');
   data[key]=input[key].trim();
  }
 }
 for(const key of ['topics','audienceCountries','audienceRegions']){
  if(input[key]!=null&&(!Array.isArray(input[key])||input[key].length>20||input[key].some(v=>typeof v!=='string'||v.length>120)))throw Error('Invalid '+key+'.');
  if(input[key]?.length)data[key]=input[key];
 }
 return data;
}
export async function submissions(request,env){
 const u=new URL(request.url),origin=request.headers.get('Origin')||'';
 if(origin&&!allowedOrigins.has(origin))return json({error:'This origin is not allowed.'},403);
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers:cors(origin)});
 try{
  if(request.method==='GET'){
   const offset=Math.max(0,Math.min(100000,Number(u.searchParams.get('offset'))||0));
   const rows=await db(env).prepare('SELECT id,url,proposal,created_at FROM event_submissions ORDER BY created_at,id LIMIT 200 OFFSET ?').bind(offset).all();
   return json({submissions:rows.results.map(r=>({id:r.id,url:r.url,proposal:JSON.parse(r.proposal),createdAt:r.created_at})),nextOffset:rows.results.length===200?offset+200:null},200,origin);
  }
  if(request.method!=='POST')return json({error:'Use GET or POST.'},405,origin);
  if(!origin)return json({error:'Please use the public submission form.'},403,origin);
  if(!request.headers.get('Content-Type')?.startsWith('application/json'))return json({error:'Use the submission form.'},415,origin);
  if(Number(request.headers.get('Content-Length')||0)>8000)return json({error:'The submission is too long.'},413,origin);
  const reader=request.body?.getReader();if(!reader)return json({error:'Please paste a public link.'},400,origin);
  const chunks=[];let size=0;
  while(true){const {value,done}=await reader.read();if(done)break;size+=value.byteLength;if(size>8000){await reader.cancel();return json({error:'The submission is too long.'},413,origin);}chunks.push(value);}
  const bytes=new Uint8Array(size);let at=0;for(const chunk of chunks){bytes.set(chunk,at);at+=chunk.byteLength;}
  let data;try{data=validate(JSON.parse(new TextDecoder().decode(bytes)));}catch(e){return json({error:e.message||'Please check the link.'},400,origin);}
  const existing=await db(env).prepare('SELECT id FROM event_submissions WHERE url=?').bind(data.url).first();
  if(existing)return json({received:true,id:existing.id,duplicate:true,message:'This link is already in the review queue.'},200,origin);
  const now=new Date().toISOString(),day=now.slice(0,10),ip=request.headers.get('CF-Connecting-IP')||'unknown';
  const digest=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(day+'|'+ip));
  const dailyClient=Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');
  const id=crypto.randomUUID();
  const result=await db(env).prepare(`INSERT OR IGNORE INTO event_submissions (id,url,proposal,created_at,daily_client)
    SELECT ?,?,?,?,? WHERE (SELECT COUNT(*) FROM event_submissions WHERE daily_client=?)<10
    AND (SELECT COUNT(*) FROM event_submissions WHERE created_at>=?)<300`).bind(id,data.url,JSON.stringify(data),now,dailyClient,dailyClient,day).run();
  if(!result.meta?.changes){
   const duplicate=await db(env).prepare('SELECT id FROM event_submissions WHERE url=?').bind(data.url).first();
   if(duplicate)return json({received:true,id:duplicate.id,duplicate:true,message:'This link is already in the review queue.'},200,origin);
   return json({error:'The submission limit has been reached. Please try again tomorrow.'},429,origin);
  }
  return json({received:true,id,message:'Link received. We’ll extract the details during the next daily check and review it before adding it to the map.'},201,origin);
 }catch(e){console.error('Submission storage request failed',e.message);return json({error:'The submission could not be saved. Your link is still in the form; please try again.'},503,origin);}
}
