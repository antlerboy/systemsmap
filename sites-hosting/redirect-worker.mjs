import {submissions} from './submission-worker.mjs';
const tangleCanonical = 'https://transduction.systems/events/';
const pstaHosts = new Set(['publicservicetransformation.com', 'www.publicservicetransformation.com', 'm.publicservicetransformation.com']);
export default {
 async fetch(request, env) {
  const incoming = new URL(request.url);
  if (!pstaHosts.has(incoming.hostname) && incoming.pathname === '/api/submissions') return submissions(request,env);
  if (request.method !== 'GET' && request.method !== 'HEAD') {
   return new Response('Method not allowed', {status:405, headers:{Allow:'GET, HEAD'}});
  }
  let target;
  if (pstaHosts.has(incoming.hostname)) {
   target = new URL('https://www.publicservicetransformation.org/');
   // Owner requested a single bulk redirect for the retired Wix site.
  } else {
   const suffix = incoming.pathname.replace(/^\/+/, '').replace(/^events\/?/, '');
   target = new URL(suffix, tangleCanonical);
   if (target.origin !== 'https://transduction.systems') return new Response('Invalid path', {status:400});
  }
  target.search = incoming.search;
  return new Response(null, {status:301, headers:{Location:target.href, 'Cache-Control':'public, max-age=300'}});
 }
};
