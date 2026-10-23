// perf.py --init: how many times three.js built a material's node graph into shader code (NodeBuilder.build), how long
// that took, and how many distinct programs came out of it (pairs: a vertex and a fragment program together, the code a
// build makes), once the office (or the map) has drawn 30 frames.
// NodeBuilder is taken from the page's own three.webgpu.js (the same URL is the same module); imported only once the
// parser is done, so the page's import map is in place before anything is loaded.
(() => {
  const S = window.__nb = { n: 0, ms: 0, types: {}, pairs: new Set() };
  document.addEventListener('readystatechange', () => {
    if (document.readyState !== 'interactive') return;
    import('https://cdn.jsdelivr.net/npm/three@0.172.0/build/three.webgpu.js').then((T) => {
      const P = T.NodeBuilder.prototype, b = P.build;
      P.build = function (...a) {
        const t = performance.now();
        try { return b.apply(this, a); } finally {
          S.n++; S.ms += performance.now() - t;
          if (this.vertexShader || this.fragmentShader) S.pairs.add(this.vertexShader + '\u0000' + this.fragmentShader);
          const k = (this.material && this.material.type) || (this.object && this.object.type) || '?';
          S.types[k] = (S.types[k] || 0) + 1;
        }
      };
    }, (e) => console.warn('nodebuilds: ' + e));
  });
  const t = setInterval(() => {
    const o = window.CO && (CO.o3 || CO.uv);
    if (!o || !(o.frames > 30)) return;
    clearInterval(t);
    const r = o.renderer;
    let cache = '?', progs = '?';
    try { cache = r._nodes.nodeBuilderCache.size; } catch (e) { /* not there */ }
    try { progs = r._pipelines.programs.vertex.size + '+' + r._pipelines.programs.fragment.size; } catch (e) { /* not there */ }
    console.warn('nodebuilds n=' + S.n + ' ms=' + Math.round(S.ms) + ' cache=' + cache + ' programs=' + progs + ' pairs=' + S.pairs.size + ' ' + JSON.stringify(S.types));
  }, 200);
})();
