/* The entry pages' space (start.html, builder.html): the office's and the Universe's own, the flyer's deep sky (u3d.js
 * deepSky; "udelej tak i loading screeny a i v start buildru", the operator, 2026-11-01) -- and the light the station
 * pictures are lit by. */
(function () {
  'use strict';
  var CO = window.CO;
  CO.E3 = {
    // the sky round a scene, a group the page keeps at its camera (as the office keeps its own); turn: the sky's
    // turn about the vertical, so its clouds stand where the page's camera sees them (the sky is painted for a camera
    // on the builder's side, looking along -x -z; a camera looking along -z wants -45 degrees)
    sky: function (scene, turn) {
      var U = CO.U3, g = U.entrySky();
      scene.background = U.look('#02090f');   // what shows where the sky is hidden: the start page's small Universe
      g.rotation.y = turn || 0; scene.add(g);
      U.idleFlush();
      return g;
    },
    // the light of the station pictures (u3d.js Preview): soft white from above, a sun from the upper left, a cool rim
    lights: function (scene) {
      var T = CO.U3.THREE;
      scene.add(new T.HemisphereLight(0xdfe8f2, 0x05070a, 0.8), new T.AmbientLight(0x1a2230, 0.7));
      var sun = new T.DirectionalLight(0xf4f8fc, 2.0); sun.position.set(-8, 12, 6); scene.add(sun);
      var rim = new T.DirectionalLight(0x00cfff, 0.6); rim.position.set(9, 2, -9); scene.add(rim);
      return sun;
    }
  };
})();
