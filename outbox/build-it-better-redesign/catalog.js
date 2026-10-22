    // Already built (new, 2026-10-22): the rebuilt apps in one row, ranked by their public traffic, arrows left and right.
    // Reads GET /api/v1/build-it-better/apps/leaderboard?sort=views|visitors (public, no key) and nothing else; the page
    // script above is not touched. A failed first read hides the section rather than showing an empty row.
    (function () {
        'use strict';
        var track = document.getElementById('bb-cat-track');
        if (!track) return;
        var prev = document.getElementById('bb-cat-prev'), next = document.getElementById('bb-cat-next');
        var sub = document.getElementById('bb-cat-sub'), sortBox = document.getElementById('bb-cat-sort');
        var cache = {}, seq = 0;

        function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
        function fmt(n) { return Number(n || 0).toLocaleString('en-US'); }
        function arrows() {
            prev.disabled = track.scrollLeft <= 2;
            next.disabled = track.scrollLeft >= track.scrollWidth - track.clientWidth - 2;
        }

        function render(d, sort) {
            track.innerHTML = '';
            var apps = d.apps || [];
            var top = apps.reduce(function (m, a) { return Math.max(m, Number(a[sort]) || 0); }, 0);
            apps.forEach(function (a, i) {
                var c = el('a', 'cat-card'); c.href = a.path || a.url; c.setAttribute('role', 'listitem');
                c.dataset.views = a.views || 0; c.dataset.visitors = a.visitors || 0;
                var head = el('div', 'cat-top'); head.appendChild(el('span', 'cat-rank', '#' + (i + 1))); head.appendChild(el('span', 'cat-open', 'Open →'));
                c.appendChild(head);
                c.appendChild(el('div', 'cat-name', a.name));
                c.appendChild(el('div', 'cat-path', a.path));
                var nums = el('div', 'cat-nums');
                [['views', 'Views'], ['visitors', 'Visitors']].forEach(function (k) {
                    var n = el('div', k[0] === sort ? 'on' : ''); n.appendChild(el('b', '', fmt(a[k[0]]))); n.appendChild(el('span', '', k[1])); nums.appendChild(n);
                });
                c.appendChild(nums);
                var bar = el('div', 'cat-bar'), fill = el('i');
                fill.style.width = (top ? Math.max(2, 100 * (Number(a[sort]) || 0) / top) : 0) + '%';
                bar.appendChild(fill); c.appendChild(bar);
                track.appendChild(c);
            });
            sub.textContent = 'Ranked by ' + sort + ' · last ' + (d.days || 30) + ' days';
            track.style.scrollBehavior = 'auto'; track.scrollLeft = 0; track.style.scrollBehavior = '';
            arrows();
        }

        function load(sort) {
            var my = ++seq;
            Array.prototype.forEach.call(sortBox.querySelectorAll('button[data-sort]'), function (b) { b.setAttribute('aria-pressed', String(b.getAttribute('data-sort') === sort)); });
            if (cache[sort]) { render(cache[sort], sort); return; }
            track.classList.add('loading');
            fetch('/api/v1/build-it-better/apps/leaderboard?sort=' + sort)
                .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
                .then(function (d) { cache[sort] = d; if (my === seq) render(d, sort); })
                .catch(function () { if (my === seq && !track.children.length) track.closest('.bb-cat').hidden = true; })
                .then(function () { if (my === seq) track.classList.remove('loading'); });
        }

        sortBox.addEventListener('click', function (e) {
            var b = e.target.closest('button[data-sort]');
            if (b && b.getAttribute('aria-pressed') !== 'true') load(b.getAttribute('data-sort'));
        });
        function step(dir) { track.scrollBy({ left: dir * Math.max(240, track.clientWidth - 80), behavior: 'smooth' }); }
        prev.addEventListener('click', function () { step(-1); });
        next.addEventListener('click', function () { step(1); });
        track.addEventListener('scroll', function () { window.requestAnimationFrame(arrows); }, { passive: true });
        window.addEventListener('resize', arrows);
        load('views');
    })();
