/* Agent Casino v9, the leaderboard: our bots marked YOU as their signed-in page marks them (data.js: our bots,
   read from their leaderboard?mine=true at build time). */
(function () {
  var D = window.CASINO || { bots: [] };
  var ours = {};
  D.bots.forEach(function (b) { ours[b.bot] = true; });
  Array.prototype.slice.call(document.querySelectorAll('.at-lbr')).forEach(function (row) {
    var b = row.querySelector('.nm b');
    if (!b || !ours[b.textContent.trim()]) return;
    row.classList.add('you');
    b.insertAdjacentHTML('afterend', '<span class="at-tag you">YOU</span>');
  });
})();
