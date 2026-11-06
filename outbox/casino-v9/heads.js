/* Agent Casino v9: every bot avatar drawn as its rendered 3D head (outbox/casino-icons, "3D v1", the operator's pick,
   2026-11-06). Their avatar names the face by a symbol, #at-bot-a ... #at-bot-f; the head of the same letter replaces it.
   Runs on what the page draws later too (cards, the picker, the finished tables). */
(function () {
  function swap(root) {
    Array.prototype.slice.call((root || document).querySelectorAll('.at-ava svg')).forEach(function (svg) {
      var use = svg.querySelector('use');
      var href = use && (use.getAttribute('href') || use.getAttribute('xlink:href') || '');
      var letter = (href.match(/#at-bot-([a-f])$/) || [])[1];
      if (!letter) return;
      var img = document.createElement('img');
      img.className = 'v9-head';
      img.src = 'art/heads/' + letter + '.webp';
      img.alt = '';
      img.draggable = false;
      svg.replaceWith(img);
    });
  }
  swap();
  new MutationObserver(function (list) {
    list.forEach(function (m) { m.addedNodes.forEach(function (n) { if (n.nodeType === 1) swap(n.parentNode || n); }); });
  }).observe(document.body, { childList: true, subtree: true });
})();
