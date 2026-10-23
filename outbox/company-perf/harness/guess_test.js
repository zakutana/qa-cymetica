// quality.js's first guess against chip names as Chrome, Edge and Firefox report them. Run with node.
const fs = require('fs');
const src = fs.readFileSync(process.argv[2], 'utf8');
const body = src.slice(src.indexOf('function guess(name)'), src.indexOf('var asked'));
global.navigator = { hardwareConcurrency: 12 };
global.window = { matchMedia: () => ({ matches: false }) };
global.matchMedia = window.matchMedia; global.screen = { width: 1920, height: 1080 };
const guess = new Function(body + '; return guess;')();
const cases = [
  ['ANGLE (AMD, AMD Radeon(TM) Graphics (0x00001638) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'low'],     // Ryzen 5 5500U (Vega 7)
  ['ANGLE (AMD, AMD Radeon(TM) Graphics (0x000013C0) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'low'],     // Ryzen 7 9700X iGPU
  ['ANGLE (AMD, AMD Radeon(TM) Vega 8 Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)', 'low'],
  ['ANGLE (AMD, AMD Radeon 780M Graphics (0x000015BF) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'medium'],
  ['ANGLE (AMD, AMD Radeon(TM) 680M Direct3D11 vs_5_0 ps_5_0, D3D11)', 'medium'],
  ['ANGLE (Intel, Intel(R) UHD Graphics 620 (0x00005917) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'low'],
  ['ANGLE (Intel, Intel(R) Iris(R) Xe Graphics (0x00009A49) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'medium'],
  ['ANGLE (Intel, Intel(R) Arc(TM) Graphics (0x00007D55) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'medium'],
  ['ANGLE (Intel, Intel(R) Arc(TM) A770 Graphics (0x000056A0) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'high'],
  ['ANGLE (NVIDIA, NVIDIA GeForce RTX 5070 Ti (0x00002C05) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'high'],
  ['ANGLE (NVIDIA, NVIDIA GeForce MX150 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'medium'],
  ['ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)', 'high'],
  ['ANGLE (AMD, AMD Radeon RX 6600 (0x000073FF) Direct3D11 vs_5_0 ps_5_0, D3D11)', 'high'],
  ['ANGLE (Apple, ANGLE Metal Renderer: Apple M1, Unspecified Version)', 'medium'],
  ['ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)', 'high'],
  ['Apple GPU', 'medium'],
  ['Mali-G78', 'low'],
  ['Adreno (TM) 740', 'medium'],
  ['ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (Subzero) (0x0000C0DE)), SwiftShader driver)', 'low'],
  ['Radeon R9 200 Series, or similar', 'medium'],
  ['', 'medium']
];
let bad = 0;
for (const [n, want] of cases) { const got = guess(n); if (got !== want) bad++; console.log((got === want ? 'ok  ' : 'BAD ') + got.padEnd(7) + ' ' + n); }
console.log(bad ? bad + ' wrong' : 'all as meant');
process.exit(bad ? 1 : 0);
