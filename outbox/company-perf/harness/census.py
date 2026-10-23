"""What the office's 825 draws a frame are: visible meshes by room and by what they are (an astronaut's parts, the
room's own, the sky, the rest), and how many share a material and a geometry (what instancing or merging could fold).
  python census.py <rec> <variant> [visit|ours]"""
import asyncio, json, sys
from pathlib import Path
from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent))
from perf import Replay, FLAGS, VIEW, DPR  # noqa: E402

JS = r"""() => {
  const o = window.CO && CO.o3; if (!o) return 'no office';
  const vis = (x) => { for (let p = x; p; p = p.parent) if (!p.visible) return false; return true; };
  const out = { rooms: {}, total: 0, agentsTotal: 0, sky: 0, other: 0, byMat: {}, layer1: 0, casters: 0 };
  const inAgent = new Set(), roomOf = new Map();
  Object.entries(o.rooms || {}).forEach(([k, r]) => {
    (r.agents || []).forEach((a) => a.g && a.g.traverse((x) => inAgent.add(x)));
    if (r.g) r.g.traverse((x) => roomOf.set(x, k));
  });
  const skyset = new Set(); if (o.sky) o.sky.traverse((x) => skyset.add(x));
  o.scene.traverse((x) => {
    if (!(x.isMesh || x.isPoints || x.isLine || x.isSprite) || !vis(x)) return;
    out.total++;
    if (x.layers.test({ mask: 2 }) || (x.layers.mask & 2)) out.layer1++;
    if (x.castShadow) out.casters++;
    const k = roomOf.get(x);
    if (inAgent.has(x)) out.agentsTotal++;
    else if (skyset.has(x)) out.sky++;
    else if (!k) out.other++;
    if (k) { const R = out.rooms[k] || (out.rooms[k] = { meshes: 0, agentParts: 0, instanced: 0 }); R.meshes++; if (inAgent.has(x)) R.agentParts++; if (x.isInstancedMesh) R.instanced++; }
    const mk = (Array.isArray(x.material) ? x.material.map((m) => m.uuid).join('+') : x.material && x.material.uuid) + '|' + (x.geometry && x.geometry.uuid);
    out.byMat[mk] = (out.byMat[mk] || 0) + 1;
  });
  const groups = Object.values(out.byMat).sort((a, b) => b - a);
  out.sameMatGeo = { groups: groups.length, top: groups.slice(0, 12), foldable: groups.filter((n) => n > 1).reduce((s, n) => s + n - 1, 0) };
  delete out.byMat;
  out.agents = Object.values(o.rooms || {}).reduce((s, r) => s + (r.agents || []).length, 0);
  // what each drawn mesh is: moving (it or a parent marked dyn, or an astronaut's), instanced, transparent, a material
  // drawn once in the whole scene (its own canvas texture: a screen), or a still opaque part whose material other
  // still opaque parts share (what one merge per material could fold)
  const dynOf = (x) => { for (let p = x; p; p = p.parent) if (p.userData && p.userData.dyn) return true; return false; };
  const matUse = new Map(), still = [];
  o.scene.traverse((x) => { if ((x.isMesh || x.isPoints || x.isSprite) && vis(x)) { const m = Array.isArray(x.material) ? x.material[0] : x.material; matUse.set(m, (matUse.get(m) || 0) + 1); } });
  const kinds = { agent: 0, dyn: 0, instanced: 0, transparent: 0, uniqueMat: 0, stillShared: 0, points: 0 };
  const shared = new Map();
  o.scene.traverse((x) => {
    if (!(x.isMesh || x.isPoints || x.isSprite) || !vis(x)) return;
    const m = Array.isArray(x.material) ? x.material[0] : x.material;
    if (x.isPoints || x.isSprite) kinds.points++;
    else if (inAgent.has(x)) kinds.agent++;
    else if (x.isInstancedMesh) kinds.instanced++;
    else if (dynOf(x)) kinds.dyn++;
    else if (m && m.transparent) kinds.transparent++;
    else if (matUse.get(m) === 1) kinds.uniqueMat++;
    else { kinds.stillShared++; const k = m.uuid + '|' + x.castShadow + x.receiveShadow + '|' + x.layers.mask + '|' + x.renderOrder; shared.set(k, (shared.get(k) || 0) + 1); }
  });
  out.kinds = kinds;
  out.stillSharedGroups = shared.size;
  // drawn from a recording (freezeRoom): meshes under a BundleGroup
  let frozen = 0; o.scene.traverse((x) => { if (x.isMesh && x.parent && x.parent.isBundleGroup) frozen++; });
  out.frozen = frozen; out.q3 = CO.Q3 ? CO.Q3.name : null;
  // the drawn meshes outside the rooms and the sky: under which of the office's own fields they hang, and how many
  const fieldOf = new Map();
  Object.keys(o).forEach((k) => { const v = o[k]; if (v && v.isObject3D && v !== o.scene && v !== o.world) v.traverse((x) => { if (!fieldOf.has(x)) fieldOf.set(x, k); }); });
  ['drift', 'flames', 'vaultPiles'].forEach((k) => { (o[k] || []).forEach((d) => { const m = d.m || d.glow || d; if (m && m.traverse) m.traverse((x) => fieldOf.set(x, k)); }); });
  const outside = {};
  o.scene.traverse((x) => {
    if (!(x.isMesh || x.isPoints || x.isSprite) || !vis(x) || roomOf.has(x) || skyset.has(x)) return;
    const k = (fieldOf.get(x) || 'world') + (x.isInstancedMesh ? ' (instanced)' : '') + (x.material && x.material.transparent ? ' (transparent)' : '') + (dynOf(x) ? ' (dyn)' : '');
    outside[k] = (outside[k] || 0) + 1;
  });
  out.outside = outside;
  out.info = o.renderer.info && o.renderer.info.render ? { drawCalls: o.renderer.info.render.drawCalls, triangles: o.renderer.info.render.triangles } : null;
  return out;
}"""


async def main():
    rec, var = Path(sys.argv[1]), Path(sys.argv[2])
    scen = sys.argv[3] if len(sys.argv) > 3 else "visit"
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context("", headless=True, args=FLAGS["fast"], channel="chrome", viewport=VIEW, device_scale_factor=DPR)
        rp = Replay(rec, var, "ours" if scen == "ours" else "out")
        await ctx.route("**/*", rp.handle)
        if len(sys.argv) > 4:
            await ctx.add_init_script(f"try {{ localStorage.removeItem('co.q3.auto'); localStorage.setItem('co.q3', '{sys.argv[4]}'); }} catch (e) {{}}")
        await ctx.route_web_socket("**/*", lambda ws: ws.close())
        pg = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await pg.goto("https://cymetica.com/company/app" + ("?visit=14" if scen == "visit" else ""))
        await pg.wait_for_function("() => window.CO && CO.o3 && CO.o3.frames > 20", timeout=60000)
        await pg.wait_for_timeout(2000)
        print(json.dumps(await pg.evaluate(JS), indent=1))
        await ctx.close()

asyncio.run(main())
