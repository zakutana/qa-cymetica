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

  // The logo picker: ten marks from logos/, swapped live on the button, the header, the welcome and the replies.
  var chosen = null;
  function read(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function paint() {
    var w = document.getElementById('nexus-chat-widget');
    if (!w || !chosen) return;
    w.querySelectorAll('.nx-logo').forEach(function (el) { if (el.innerHTML !== chosen.svg) el.innerHTML = chosen.svg; });
    var inner = chosen.svg.replace(/^<svg[^>]*>|<\/svg>$/g, '');
    var disc = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><circle cx="24" cy="24" r="24" fill="#00FF88"/><g fill="#06090F">' + inner + '</g></svg>';
    w.style.setProperty('--nx-mark', 'url("data:image/svg+xml,' + encodeURIComponent(disc) + '")');
  }
  fetch('/_nx/logos/logos.json').then(function (r) { return r.json(); }).then(function (list) {
    return Promise.all(list.map(function (l) {
      return fetch('/_nx/logos/' + l.file).then(function (r) { return r.text(); }).then(function (svg) { l.svg = svg.trim(); return l; });
    }));
  }).then(function (list) {
    var style2 = document.createElement('style');
    style2.textContent = '.nxd .nxd-logos{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.nxd .nxd-logos button{all:unset;cursor:pointer;display:flex;flex-direction:column;align-items:center;gap:2px;font:500 10px "IBM Plex Mono",monospace;color:#7E90A1}' +
      '.nxd .nxd-logos i{display:block;width:36px;height:36px;border-radius:50%;background:#00FF88;color:#06090F;outline:2px solid transparent;outline-offset:2px}.nxd .nxd-logos i svg{display:block;width:100%;height:100%}.nxd .nxd-logos button:hover i{outline-color:#2B3A49}.nxd .nxd-logos button.on{color:#E9EFF5}.nxd .nxd-logos button.on i{outline-color:#E9EFF5}.nxd .nxd-name{margin-top:6px;color:#E9EFF5;font-size:12px}';
    document.head.appendChild(style2);
    var h = document.createElement('h6');
    h.textContent = 'Logo';
    var grid = document.createElement('div');
    grid.className = 'nxd-logos';
    var name = document.createElement('div');
    name.className = 'nxd-name';
    function pick(l, btn) {
      chosen = l;
      try { localStorage.setItem('nx_logo', l.file); } catch (e) {}
      grid.querySelectorAll('button').forEach(function (b) { b.classList.remove('on'); });
      btn.classList.add('on');
      name.textContent = parseInt(l.file, 10) + '. ' + l.name;
      paint();
    }
    var saved = read('nx_logo');
    list.forEach(function (l) {
      var b = document.createElement('button');
      b.type = 'button';
      b.title = l.name + ': ' + l.idea;
      b.innerHTML = '<i>' + l.svg + '</i>' + parseInt(l.file, 10);
      b.addEventListener('click', function () { pick(l, b); });
      grid.appendChild(b);
      if (l.file === saved || (!saved && l.file === '01.svg')) setTimeout(function () { pick(l, b); }, 0);
    });
    box.insertBefore(name, box.children[1]);
    box.insertBefore(grid, name);
    box.insertBefore(h, grid);
    new MutationObserver(paint).observe(document.body, { childList: true, subtree: false });
    var tries = 0;
    var wait = setInterval(function () {
      var w = document.getElementById('nexus-chat-widget');
      if (w) {
        clearInterval(wait);
        paint();
        new MutationObserver(paint).observe(w.querySelector('.nexus-messages'), { childList: true });
      } else if (++tries > 100) clearInterval(wait);
    }, 100);
  });
})();
