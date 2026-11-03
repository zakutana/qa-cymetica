/* The presenter's bar on the mock, not part of the design: each button drives the real chat with a scripted reply. */
(function () {
  if (window.self !== window.top) return;
  var send = function (text) { return function () { window._nexusPrefill(text, { send: true }); }; };
  var plan = function (p) {
    return function () {
      fetch('/__demo/plan', { method: 'POST', body: JSON.stringify({ plan: p }) }).then(function () {
        if (window.__NX_DEMO) window.__NX_DEMO.in = p !== 'out';
        location.reload();
      });
    };
  };
  var groups = [
    ['Replies', [
      ['Full answer', send('Show the top apps by upside')],
      ['Options', send('Give me options')],
      ['Token launch', send('Launch a token')],
      ['Connect exchange', send('Connect an exchange')]
    ]],
    ['States', [
      ['Low balance', send('Answer with a low balance warning')],
      ['Degraded', send('Answer in degraded mode')],
      ['Error', send('Show an error')],
      ['Reconnecting', send('Show a reconnect')],
      ['Offline', function () {
        send('What happens when I go offline?')();
        setTimeout(function () { window.dispatchEvent(new Event('offline')); }, 250);
        setTimeout(function () { window.dispatchEvent(new Event('online')); }, 4000);
      }],
      ['New-reply dot', function () { fetch('/__demo/pending', { method: 'POST' }).then(function () { try { localStorage.setItem('nexus_collapsed', 'true'); } catch (e) {} location.reload(); }); }]
    ]],
    ['Plan', [
      ['Premium', plan('premium')],
      ['Pay per use', plan('payg')],
      ['Covered', plan('covered')],
      ['Paper', plan('paper')],
      ['Low funds', plan('broke')]
    ]]
  ];
  var css = '.nxd{position:fixed;left:16px;bottom:16px;z-index:999999;font:12px/1.3 "IBM Plex Sans",sans-serif;color:#A4B3C2;width:232px;background:rgba(13,20,28,.94);border:1px dashed #2B3A49;border-radius:12px;padding:8px 10px 10px}' +
    '.nxd summary{cursor:pointer;font:600 11px "IBM Plex Mono",monospace;letter-spacing:.06em;color:#7E90A1;list-style:none}.nxd summary::-webkit-details-marker{display:none}' +
    '.nxd h6{margin:9px 0 4px;font:600 10px "IBM Plex Mono",monospace;letter-spacing:.08em;text-transform:uppercase;color:#7E90A1}' +
    '.nxd div{display:flex;flex-wrap:wrap;gap:4px}.nxd button{all:unset;cursor:pointer;padding:3px 7px;border:1px solid #1E2A36;border-radius:6px;color:#A4B3C2}.nxd button:hover{border-color:#2B3A49;color:#E9EFF5}' +
    'body.nexus-sidebar-pinned-left.nexus-panel-open .nxd{left:auto;right:16px}' +
    '@media (max-width:768px){.nxd{display:none}}';
  var style = document.createElement('style');
  style.textContent = css;
  document.head.appendChild(style);
  var box = document.createElement('details');
  box.className = 'nxd';
  box.open = true;
  box.innerHTML = '<summary>DEMO CONTROLS (not in the design)</summary>';
  groups.forEach(function (g) {
    var h = document.createElement('h6');
    h.textContent = g[0];
    box.appendChild(h);
    var row = document.createElement('div');
    g[1].forEach(function (b) {
      var el = document.createElement('button');
      el.type = 'button';
      el.textContent = b[0];
      el.addEventListener('click', b[1]);
      row.appendChild(el);
    });
    box.appendChild(row);
  });
  document.body.appendChild(box);
})();
