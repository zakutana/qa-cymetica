/* Mock only: land on the demo report, so the page opens on what is being judged. */
(function () {
  function go() {
    var b = document.getElementById('mmDemo');
    if (b) { b.click(); setTimeout(function () { window.scrollTo(0, 0); var r = document.getElementById('mmReport'); if (r) r.scrollIntoView({ block: 'start' }); }, 60); }
  }
  if (document.readyState === 'complete') go(); else window.addEventListener('load', go);
})();
