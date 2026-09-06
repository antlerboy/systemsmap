const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const fields=new Map(),handlers=new Map();
function el(s){if(!fields.has(s))fields.set(s,{value:'',textContent:'',addEventListener:(n,cb)=>handlers.set(s+':'+n,cb),querySelector:()=>null});return fields.get(s);}
let requestBody,resetCount=0,fail=false;
const context={URL,URLSearchParams,Intl,Date,TextEncoder,console,setTimeout,location:{hostname:'test',search:'',pathname:'/',hash:''},AbortSignal,fetch:async(url,options)=>{requestBody=JSON.parse(options.body);return {ok:!fail,json:async()=>fail?{error:'Storage unavailable'}:{received:true,id:'12345678-test',message:'Link received.'}}},history:{replaceState(){}},document:{querySelector:el,addEventListener(){}},FormData:class{constructor(form){return Object.entries(form.values)}}};
context.window=context;vm.createContext(context);
let src=fs.readFileSync('dist/app.js','utf8').replace('  load();','  globalThis.test={match,place,focus,languages,ics};');
vm.runInContext(src,context);
const e={id:'polska',title:'Polish event',organiser:'SCiO Polska',organisationIds:['scio'],description:'',start:'2026-09-15T18:00:00+02:00',end:'2026-09-15T19:30:00+02:00',format:'online',country:'',location:'Online',audienceCountries:['Poland'],audienceRegions:[],language:'Polish',languageRequirement:'Discussion in Polish',interpretation:'No interpretation',access:'All welcome',topics:['systems'],notes:[],calendarEligible:true,allDay:false,updatedAt:'2026-09-06T12:00:00Z',sequence:0,url:'https://example.org/event'};
el('#period').value='all';el('#country').value='Poland';el('#language').value='Polish';el('#topics input:checked').value='';
assert(context.test.match(e));el('#language').value='English';assert(!context.test.match(e));el('#language').value='';el('#country').value='Europe';assert(!context.test.match(e));
assert(context.test.place(e).includes('Poland'));assert(!context.test.place(e).includes('anywhere'));assert(context.test.ics([e]).replace(/\r\n /g,'').includes('Language requirements: Discussion in Polish'));
const values={url:'https://example.org/event',kind:'auto',title:'',organiser:'',start:'',end:'',startTime:'',endTime:'',timezone:'',location:'',topic:'',description:'',language:'',languageRequirement:'',interpretation:'',access:'',audienceCountries:'',audienceRegions:''};
(async()=>{
const button={disabled:false},form={values,querySelector:()=>button,reset:()=>resetCount++};
await handlers.get('#submission:submit')({preventDefault(){},currentTarget:form});
assert.equal(requestBody.url,values.url);assert.equal(requestBody.title,null);assert.equal(requestBody.kind,'auto');assert.equal(resetCount,1);assert.equal(button.disabled,false);assert(el('#submission-status').textContent.includes('Link received'));
fail=true;await handlers.get('#submission:submit')({preventDefault(){},currentTarget:form});assert.equal(resetCount,1);assert.equal(button.disabled,false);assert(el('#submission-status').textContent.includes('Storage unavailable'));
console.log('Verified country/language filtering, calendar details, anonymous receipt, and preserved input on submission failure.');
})().catch(error=>{console.error(error);process.exitCode=1;});
