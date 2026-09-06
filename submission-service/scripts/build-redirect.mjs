import fs from 'node:fs';
fs.rmSync('dist',{recursive:true,force:true});
fs.mkdirSync('dist/server',{recursive:true});
fs.copyFileSync('redirect-worker.mjs','dist/server/index.js');

fs.copyFileSync('submission-worker.mjs','dist/server/submission-worker.mjs');
fs.mkdirSync('dist/.openai',{recursive:true});
fs.copyFileSync('.openai/hosting.json','dist/.openai/hosting.json');
fs.cpSync('drizzle','dist/.openai/drizzle',{recursive:true});
