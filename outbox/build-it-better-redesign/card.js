        // ── board card, redesigned 2026-10-22 ──────────────────────────────────────
        // The same data and the same links as the card it replaces (the ticket opens it here, "open →" goes to the
        // build, the numbers go to its public traffic, the late and verdict pills keep their words), laid out as a
        // preview of the app, its name, its 24 h clock as a bar, and its traffic as four numbers.
        // preview(): the build's own preview_url once the API carries one (it does not today), else the app's
        // /og/app card. window.BB_PREVIEWS exists only in the mockup, which pictured the live apps itself.
        function preview(url, own) {
            var path = ''; try { path = new URL(url, location.href).pathname; } catch (e) { return own || ''; }
            var shot = (window.BB_PREVIEWS || {})[path];
            var slug = path.replace(/^\/+|\/+$/g, '').replace(/\//g, '-');
            return own || shot || (slug ? '/og/app/' + slug + '.png' : '');
        }
        function card(b) {
            function add(parent, tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; parent.appendChild(e); return e; }
            var el = document.createElement('div'); el.className = 'bb-card ' + (b.stage || ''); el.id = 'bbc-' + b.ticket;
            if (b.stage === 'shipped') {
                var pv = add(el, b.our_url ? 'a' : 'div', 'pv');
                if (b.our_url) { pv.href = b.our_url; pv.tabIndex = -1; pv.setAttribute('aria-hidden', 'true'); }
                add(pv, 'span', 'pv-mono', String(b.app_name || '?').replace(/[^A-Za-z0-9 ]/g, ' ').trim().split(/\s+/).slice(0, 2).map(function (w) { return w.charAt(0); }).join('').toUpperCase());
                var src = b.our_url ? preview(b.our_url, b.preview_url) : (b.preview_url || '');
                if (src) { var img = add(pv, 'img'); img.loading = 'lazy'; img.alt = ''; img.onerror = function () { if (img.parentNode) img.parentNode.removeChild(img); }; img.src = src; }
                var badges = add(pv, 'div', 'pv-badges');
                add(badges, 'span', 'bb-pill ' + (b.on_time ? 'pos' : (b.on_time === false ? 'neg' : '')), dur(b.elapsed_seconds) + (b.on_time === false ? ', late' : ''));
                if (b.verdict) add(badges, 'span', 'bb-pill ' + (b.verdict === 'pass' ? 'pos' : 'neg'), 'verdict: ' + b.verdict);
            }
            var body = add(el, 'div', 'body');
            add(body, 'div', 'n', b.app_name);
            add(body, 'div', 'w', b.improvements);
            var m = add(body, 'div', 'm');
            if (b.stage === 'requested') {
                m.textContent = 'Scope proposed · waiting on the requester to accept';
            } else if (b.stage !== 'shipped') {
                var bar = add(m, 'div', 'bb-bar' + (b.on_time === false ? ' late' : ''));
                add(bar, 'i').style.width = Math.min(100, 100 * (b.elapsed_seconds || 0) / 86400) + '%';
                add(m, 'span', '', (b.spec_status === 'accepted' ? '' : 'waiting on scope accept · ') + 'clock ' + dur(b.elapsed_seconds) + ' of 24h');
                if (b.on_time === false) add(m, 'span', 'bb-pill neg', 'past its 24 h · not shipped');   // past its own deadline and not shipped: say so (ET-26174)
            }
            if (b.traffic) {   // public traffic of the shipped app, last 30 days
                var tr = add(body, 'a', 'tr'); tr.href = '/build-it-better/stats?app=' + encodeURIComponent(b.traffic.path);
                tr.title = 'Public traffic for this app, last ' + b.traffic.days + ' days';
                [['views', 'views'], ['visitors', 'visitors'], ['uses', 'uses'], ['likes', 'likes']].forEach(function (k) {
                    var s = add(tr, 'span'); add(s, 'b', '', Number(b.traffic[k[0]]).toLocaleString('en-US')); add(s, 'small', '', k[1]);
                });
            }
            var t = add(body, 'div', 't');
            var tk = add(t, 'a', 'tk', b.ticket); tk.href = '?t=' + encodeURIComponent(b.ticket);
            tk.addEventListener('click', function (ev) { ev.preventDefault(); openTicket(b.ticket); });
            add(t, 'span', 'bb-pill', b.requester_kind === 'agent' ? 'AI agent' : 'person');
            if (b.stage === 'shipped' && b.our_url) { var o = add(t, 'a', 'open', 'open →'); o.href = b.our_url; }
            return el;
        }
        // ── end of the board card ──────────────────────────────────────────────────
