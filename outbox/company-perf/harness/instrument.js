// Injected before any page script: what the page costs, read back by perf.py. Nothing here changes what is drawn.
(() => {
  if (window.__perf) return;
  const M = window.__perf = {
    frames: [], longtasks: [], marks: {}, devices: 0, contexts: 0, pipelinesSync: 0, pipelinesAsync: 0,
    shaderModules: 0, syncPipeMs: 0, textures: 0, texBytesPeak: 0, texBytesLive: 0, renderers: 0, errors: []
  };
  const f = (t) => { M.frames.push(t); requestAnimationFrame(f); };
  requestAnimationFrame(f);
  try {
    new PerformanceObserver((l) => { for (const e of l.getEntries()) M.longtasks.push([e.startTime, e.duration]); })
      .observe({ type: 'longtask', buffered: true });
  } catch (e) { /* none */ }
  window.addEventListener('error', (e) => { M.errors.push(String(e.message).slice(0, 200)); });
  // the loading screens: the page's (#boot) going, the Universe stage's (#uvload) shown and hidden
  const watch = () => {
    const now = performance.now(), b = document.getElementById('boot');
    if (!M.marks.bootGone && (!b || b.classList.contains('gone'))) M.marks.bootGone = now;
    const u = document.getElementById('uvload');
    if (u) {
      if (!u.hidden && !M.marks.uvLoadOn) M.marks.uvLoadOn = now;
      if (u.hidden && M.marks.uvLoadOn && !M.marks.uvLoadOff) M.marks.uvLoadOff = now;
    }
  };
  const mo = new MutationObserver(watch);
  const start = () => { mo.observe(document.documentElement, { subtree: true, childList: true, attributes: true, attributeFilter: ['class', 'hidden'] }); watch(); };
  if (document.documentElement) start(); else document.addEventListener('DOMContentLoaded', start);
  // WebGPU: devices, canvases, shader modules and pipelines made, textures held (an estimate of their bytes)
  if (window.GPUAdapter && window.GPUDevice) {
    const A = GPUAdapter.prototype, rd = A.requestDevice;
    A.requestDevice = function (...a) { M.devices++; return rd.apply(this, a); };
    const D = GPUDevice.prototype;
    const crp = D.createRenderPipeline;
    D.createRenderPipeline = function (...a) { const t = performance.now(); const r = crp.apply(this, a); M.pipelinesSync++; M.syncPipeMs += performance.now() - t; return r; };
    const crpa = D.createRenderPipelineAsync;
    D.createRenderPipelineAsync = function (...a) { M.pipelinesAsync++; return crpa.apply(this, a); };
    const csm = D.createShaderModule;
    D.createShaderModule = function (...a) { M.shaderModules++; return csm.apply(this, a); };
    const sizes = new WeakMap(), ct = D.createTexture;
    D.createTexture = function (d) {
      const tex = ct.call(this, d);
      try {
        const s = d.size, w = s.width != null ? s.width : s[0], h = (s.height != null ? s.height : s[1]) || 1, l = (s.depthOrArrayLayers != null ? s.depthOrArrayLayers : s[2]) || 1;
        const fm = String(d.format), bpp = /32float/.test(fm) ? (/rgba/.test(fm) ? 16 : 4) : /16float/.test(fm) ? (/rgba/.test(fm) ? 8 : 2) : 4;
        const b = w * h * l * bpp * (d.sampleCount || 1) * ((d.mipLevelCount || 1) > 1 ? 1.333 : 1);
        sizes.set(tex, b); M.textures++; M.texBytesLive += b; if (M.texBytesLive > M.texBytesPeak) M.texBytesPeak = M.texBytesLive;
      } catch (e) { /* unknown size */ }
      return tex;
    };
    const T = GPUTexture.prototype, td = T.destroy;
    T.destroy = function () { const b = sizes.get(this); if (b) { M.texBytesLive -= b; sizes.delete(this); } return td.call(this); };
    // draw calls, by the kind of pass they are in (what the main thread pays for, object by object): a pass with a
    // depth target only is a shadow map; the rest by their colour target's sample count and size
    // (three.js encodes a pass inside another one's lifetime -- the floors' mirror while the main pass is open -- so a
    // draw is counted to the pass encoder it is called on, not to the last one begun)
    M.passes = {}; const kinds = new WeakMap();
    const CE = GPUCommandEncoder.prototype, brp = CE.beginRenderPass;
    CE.beginRenderPass = function (d) {
      const ca = d && d.colorAttachments && d.colorAttachments[0];
      let kind = 'depth-only';
      if (ca && ca.view) { const t = ca.view.__tex; kind = t ? (t.sampleCount > 1 ? 'msaa' : 'single') + ' ' + t.width + 'x' + t.height : 'canvas?'; }
      const b = M.passes[kind] || (M.passes[kind] = { passes: 0, draws: 0 }); b.passes++;
      const pe = brp.call(this, d); kinds.set(pe, b); return pe;
    };
    const RP = GPURenderPassEncoder.prototype;
    ['draw', 'drawIndexed', 'drawIndirect', 'drawIndexedIndirect'].forEach((k) => {
      const f = RP[k]; RP[k] = function (...a) { const b = kinds.get(this); if (b) b.draws++; return f.apply(this, a); };
    });
    const TV = GPUTexture.prototype, cv = TV.createView;
    TV.createView = function (...a) { const v = cv.apply(this, a); try { v.__tex = this; } catch (e) { /* frozen */ } return v; };
    // a frame drawn: one getCurrentTexture per canvas per drawn frame (the rAF ticks above run whether or not a
    // scene draws in them; this is the scenes' own frame rate)
    M.present = []; M.gpuSpans = [];
    const C = window.GPUCanvasContext && GPUCanvasContext.prototype;
    if (C) { const gct = C.getCurrentTexture; C.getCurrentTexture = function () { M.present.push(performance.now()); return gct.call(this); }; }
    // the GPU busy: each submit's work, from when it was handed over (or the GPU finished the one before) to when it
    // was done. An estimate: the "done" is seen when the main thread runs the promise, late if it is busy.
    const Qp = GPUQueue.prototype, sub = Qp.submit;
    let lastDone = 0;
    Qp.submit = function (b) {
      const ts = performance.now(), r = sub.call(this, b);
      try { this.onSubmittedWorkDone().then(() => { const te = performance.now(), s = Math.max(ts, lastDone); if (te > s) M.gpuSpans.push([s, te]); lastDone = te; }); } catch (e) { /* fine */ }
      return r;
    };
  }
  const gc = HTMLCanvasElement.prototype.getContext;
  HTMLCanvasElement.prototype.getContext = function (k, ...a) { if (k === 'webgpu') M.contexts++; return gc.call(this, k, ...a); };
  M.mark = (k) => { M.marks[k] = performance.now(); };
})();
