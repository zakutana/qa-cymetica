/* The entry pages' space (start.html, builder.html): the office's own -- its navy, its nebulae and their teal and
 * green glow, its stars (u3d.js spaceSky) -- and the light the station pictures are lit by. Not a near-black void:
 * "pozadi je vsude moc tmave ... tak tmave to neni vubec v univerzu pak ani v office" (the operator, 2026-10-20). */
(function () {
  'use strict';
  var CO = window.CO;
  CO.E3 = {
    // the sky round a scene, a group the page keeps at its camera (as the office keeps its own); turn: the sky's
    // turn about the vertical, so its nebulae stand where the office's camera sees them (the office looks along
    // -x -z; a camera looking along -z wants -45 degrees)
    sky: function (scene, turn) {
      var U = CO.U3, T = U.THREE, g = U.spaceSky(true);
      scene.background = new T.Color(U.LOOK.sky);
      g.rotation.y = turn || 0; scene.add(g);
      // the far glows of the station pictures: cyan, green and blue light across the sky behind
      var far = new T.Group(); far.rotation.y = turn || 0; g.add(far);
      [[0x00cfff, 0.16, [-170, 40, -220], 360], [0x00ff88, 0.08, [140, -70, -250], 300], [0x3b82f6, 0.08, [-250, -90, 40], 300]].forEach(function (s) {
        var sp = U.glowSprite(s[0], s[1], s[3]); sp.position.set(s[2][0], s[2][1], s[2][2]); far.add(sp);
      });
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
