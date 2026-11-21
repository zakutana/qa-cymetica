/* MethylMap redesign: layout only, on top of their own render (hb-methylmap.js). Every word on the page is theirs;
   this file moves and regroups what their script drew, and re-applies itself each time they re-render #mmReport. */
(function () {
  var rep = document.getElementById('mmReport');
  if (!rep) return;
  var ORDER = ['mm-c2', 'mm-c1', 'mm-c0', 'mm-cn'];

  function cls(el) { for (var i = 0; i < ORDER.length; i++) if (el.classList.contains(ORDER[i])) return ORDER[i]; return 'mm-cn'; }
  function el(tag, c, text) { var e = document.createElement(tag); if (c) e.className = c; if (text != null) e.textContent = text; return e; }
  function sec(id) { return rep.querySelector('section[aria-labelledby="' + id + '"]'); }
  function ownText(node) {
    return Array.prototype.filter.call(node.childNodes, function (n) { return n.nodeType === 3; }).map(function (n) { return n.textContent; }).join(' ').replace(/\s+/g, ' ').trim();
  }

  function apply() {
    var head = sec('mmResH'), tiles = document.getElementById('mmTiles');
    if (!head || !tiles || head.classList.contains('rd-head')) return;
    rep.classList.add('rd');
    head.classList.add('rd-head');
    header(head, tiles);
    genes(head, tiles);
    pathway();
    combos();
    nutrients(tiles);
    settle();
    setTimeout(settle, 0);
  }

  // their scroll reveal (biomiv-reveal.js) arms single blocks; a block we moved into a card would rise apart from it
  function settle() {
    Array.prototype.forEach.call(rep.querySelectorAll('.bm-reveal'), function (n) { n.classList.remove('bm-reveal'); });
  }

  // title and coverage on the left, the three actions on the right, then the four counts as one proportional row
  function header(head, tiles) {
    var top = el('div', 'rd-top'), title = el('div', 'rd-title');
    ['.mm-demo-flag', 'h2', '.mm-cover', '.mm-meta'].forEach(function (q) { var n = head.querySelector(':scope > ' + q); if (n) title.appendChild(n); });
    top.appendChild(title);
    var actions = head.querySelector(':scope > .mm-row');
    if (actions) top.appendChild(actions);
    head.insertBefore(top, head.firstChild);
    var legend = head.querySelector(':scope > .mm-legend');
    if (legend) Array.prototype.forEach.call(legend.children, function (li) {
      var n = tiles.querySelectorAll('.mm-tile.' + cls(li)).length;
      li.style.setProperty('--n', n);
      li.insertBefore(el('b', 'rd-n', String(n)), li.firstChild);
    });
  }

  // the 13 tiles and the 13 gene cards become one view: the list on the left, the opened gene beside it
  function genes(head, tiles) {
    var list = sec('mmGenesH');
    if (!list) return;
    var cards = Array.prototype.slice.call(list.querySelectorAll(':scope > details.mm-gene'));
    var split = el('div', 'rd-split'), detail = el('div', 'rd-detail');
    var intro = el('div', 'rd-genes-h');
    ['h2', '.mm-lede'].forEach(function (q) { var n = list.querySelector(':scope > ' + q); if (n) intro.appendChild(n); });
    head.insertBefore(intro, tiles);
    head.insertBefore(split, tiles);
    split.appendChild(tiles);
    split.appendChild(detail);
    cards.forEach(function (d) { detail.appendChild(d); });
    list.classList.add('rd-empty');

    Array.prototype.forEach.call(tiles.children, function (li) {
      var d = document.getElementById('mmGene-' + li.getAttribute('data-gene')), btn = li.querySelector('button');
      var p = d && d.querySelector('.mm-gene-body > p');
      var sub = btn && btn.querySelector('.mm-sub');
      if (p && sub) btn.insertBefore(el('span', 'rd-role', ownText(p)), sub);
      var parts = sub ? sub.textContent.split(' · ') : [];
      if (parts.length === 2) { sub.textContent = ''; sub.appendChild(el('span', '', parts[0])); sub.appendChild(el('span', '', parts[1])); }
    });

    function select(id) {
      Array.prototype.forEach.call(tiles.children, function (li) {
        var on = li.getAttribute('data-gene') === id;
        li.classList.toggle('rd-on', on);
        li.querySelector('button').setAttribute('aria-pressed', on ? 'true' : 'false');
      });
      cards.forEach(function (d) {
        var on = d.id === 'mmGene-' + id;
        d.classList.toggle('rd-on', on);
        if (on) d.open = true;
      });
    }
    tiles.addEventListener('click', function (e) {
      var li = e.target.closest('.mm-tile');
      if (!li) return;
      e.stopPropagation();
      select(li.getAttribute('data-gene'));
      if (detail.getBoundingClientRect().top > tiles.getBoundingClientRect().bottom - 4) detail.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, true);
    var first = Array.prototype.slice.call(tiles.children).sort(function (a, b) { return ORDER.indexOf(cls(a)) - ORDER.indexOf(cls(b)); })[0];
    if (first) select(first.getAttribute('data-gene'));
  }

  // the sentence that names the slow steps leads the map
  function pathway() {
    var s = sec('mmMapH');
    if (!s) return;
    s.classList.add('rd-map');
    var slow = s.querySelector(':scope > p:not([class])'), lede = s.querySelector(':scope > .mm-lede');
    var legend = s.querySelector(':scope > .mm-legend'), map = s.querySelector(':scope > .mm-map');
    if (slow && lede) { slow.className = 'rd-slow'; s.insertBefore(slow, lede); }
    if (legend && map) s.insertBefore(legend, map);
    // a node with two lines of text gets a box tall enough for both (theirs leaves the second line under the box)
    Array.prototype.forEach.call(s.querySelectorAll('.mm-map g.n'), function (g) {
      var r = g.querySelector('rect');
      if (r && g.querySelectorAll('text').length > 1) r.setAttribute('height', String(+r.getAttribute('height') + 22));
    });
  }

  function combos() {
    var s = sec('mmComboH');
    if (!s) return;
    s.classList.add('rd-combos');
    var hits = s.querySelectorAll(':scope > .mm-caution');
    if (!hits.length) return;
    var grid = el('div', 'rd-grid');
    s.insertBefore(grid, hits[0]);
    Array.prototype.forEach.call(hits, function (c) { grid.appendChild(c); });
  }

  // one card per gene instead of one long list: the nutrient rows first, then label and text pairs
  function nutrients(tiles) {
    var s = sec('mmNutH');
    if (!s) return;
    s.classList.add('rd-nutsec');
    var byLabel = {};
    Array.prototype.forEach.call(tiles.children, function (li) { byLabel[li.querySelector('b').textContent] = cls(li); });
    var heads = Array.prototype.slice.call(s.querySelectorAll(':scope > h3'));
    if (!heads.length) return;
    var wrap = el('div', 'rd-nuts');
    s.insertBefore(wrap, heads[0]);
    heads.forEach(function (h3) {
      var ul = h3.nextElementSibling, m = /^(.*) \((.*)\)$/.exec(h3.textContent);
      var card = el('article', 'rd-nut ' + (m && byLabel[m[1]] || 'mm-cn'));
      if (m) { h3.textContent = ''; h3.appendChild(el('b', '', m[1])); h3.appendChild(el('span', 'mm-word', m[2])); }
      card.appendChild(h3);
      if (ul && ul.tagName === 'UL') {
        Array.prototype.forEach.call(ul.children, function (li) {
          if (li.querySelector('strong')) { li.className = 'rd-nu'; return; }
          var kv = /^([A-Z][A-Za-z ]{1,24}): (.+)$/.exec(li.textContent);
          if (!kv) { li.className = 'rd-line'; return; }
          li.className = 'rd-kv';
          li.textContent = '';
          li.appendChild(el('span', 'rd-k', kv[1]));
          li.appendChild(el('span', 'rd-v', kv[2]));
        });
        card.appendChild(ul);
      }
      wrap.appendChild(card);
    });
  }

  new MutationObserver(apply).observe(rep, { childList: true });
  apply();
})();
