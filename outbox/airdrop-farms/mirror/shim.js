/* Mockup only, not part of the design: answers the page's /api/v1/airdrop-farm/* calls from the files in data/,
   so this copy of cymetica.com/airdrop-farmer runs locally as the signed-in operator saw it on 2026-10-29
   (farms and config read live that day; plan and status rebuilt from his screenshots: $94 in his wallets,
   Upshift with $8.15 in, $6.96 now). */
(function () {
  var real = window.fetch.bind(window);
  var FILES = { '/farms': 'data/farms.json', '/config': 'data/config.json', '/plan': 'data/plan.json', '/status': 'data/status.json' };
  window.fetch = function (url, opts) {
    var u = String(url && url.url || url);
    var m = u.match(/\/api\/v1\/airdrop-farm(\/[a-z]+)/);
    if (m) {
      var f = FILES[m[1]];
      if (f) return real(f);
      return Promise.resolve(new Response('{"detail":"not in the mockup"}', { status: 404, headers: { 'Content-Type': 'application/json' } }));
    }
    if (/^\/api\//.test(u)) return Promise.resolve(new Response('{}', { status: 404, headers: { 'Content-Type': 'application/json' } }));
    return real(url, opts);
  };
  window.hasSession = function () { return true; };
})();
