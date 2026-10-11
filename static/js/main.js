/* Marketora front-end behaviour (no dependencies) */
(function () {
    'use strict';

    const ROOT = document.body.getAttribute('data-root') || '';   // portal prefix, e.g. /seller
    const $ = (sel, root) => (root || document).querySelector(sel);
    const $$ = (sel, root) => Array.from((root || document).querySelectorAll(sel));

    /* ---------- category drawer ---------- */
    function setDrawer(open) { document.body.classList.toggle('drawer-open', open); }
    document.addEventListener('click', function (e) {
        if (e.target.closest('[data-open-drawer]')) { e.preventDefault(); setDrawer(true); }
        else if (e.target.closest('[data-close-drawer]')) { setDrawer(false); }
    });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') setDrawer(false); });

    const drawerFilter = $('#drawer-filter');
    if (drawerFilter) {
        drawerFilter.addEventListener('input', function () {
            const term = drawerFilter.value.trim().toLowerCase();
            $$('.drawer details').forEach(function (d) {
                const subs = $$('.subs a:not(.all)', d);
                let any = d.querySelector('summary span').textContent.toLowerCase().includes(term);
                subs.forEach(function (a) {
                    const hit = !term || a.textContent.toLowerCase().includes(term);
                    a.classList.toggle('hidden', !hit);
                    if (hit && term) any = true;
                });
                d.classList.toggle('hidden', !any);
                d.open = !!term && any;
            });
        });
    }

    /* ---------- confirm dialogs: <form data-confirm="Are you sure?"> ---------- */
    document.addEventListener('submit', function (e) {
        const msg = e.target.getAttribute('data-confirm');
        if (msg && !window.confirm(msg)) e.preventDefault();
    });

    /* ---------- horizontal scrollers (product rows + category carousel) ---------- */
    $$('.scroller-wrap').forEach(function (wrap) {
        const scroller = $('.scroller', wrap);
        if (!scroller) return;
        const step = function () { return Math.max(scroller.clientWidth * 0.85, 200); };
        const go = function (dir) {
            const max = scroller.scrollWidth - scroller.clientWidth;
            if (dir > 0 && scroller.scrollLeft >= max - 4) scroller.scrollTo({ left: 0 });
            else if (dir < 0 && scroller.scrollLeft <= 4) scroller.scrollTo({ left: max });
            else scroller.scrollBy({ left: dir * step() });
        };
        $('.scroll-btn.prev', wrap).addEventListener('click', function () { go(-1); });
        $('.scroll-btn.next', wrap).addEventListener('click', function () { go(1); });

        const auto = parseInt(wrap.getAttribute('data-autoplay') || '0', 10);
        if (auto) {
            let timer = setInterval(function () { go(1); }, auto);
            wrap.addEventListener('mouseenter', function () { clearInterval(timer); });
            wrap.addEventListener('mouseleave', function () { timer = setInterval(function () { go(1); }, auto); });
        }
    });

    /* ---------- hero slider: slow rotation + periodic refresh with a new set of products ---------- */
    const hero = $('.hero');
    if (hero) {
        const dotsBox = $('.hero-dots', hero);
        const DELAY = parseInt(hero.getAttribute('data-delay') || '6000', 10);
        const REFRESH = parseInt(hero.getAttribute('data-refresh') || '0', 10);
        let slides = $$('.hero-slide', hero), dots = [], index = 0, timer = null;

        function buildDots() {
            dotsBox.innerHTML = '';
            dots = slides.map(function (_, i) {
                const b = document.createElement('button');
                b.type = 'button';
                b.setAttribute('aria-label', 'Slide ' + (i + 1));
                b.addEventListener('click', function () { show(i); restart(); });
                dotsBox.appendChild(b);
                return b;
            });
        }
        function show(i) {
            index = (i + slides.length) % slides.length;
            slides.forEach(function (s, n) { s.classList.toggle('active', n === index); });
            dots.forEach(function (d, n) { d.classList.toggle('active', n === index); });
        }
        function restart() { clearInterval(timer); timer = setInterval(function () { show(index + 1); }, DELAY); }
        $('.hero-nav.prev', hero).addEventListener('click', function () { show(index - 1); restart(); });
        $('.hero-nav.next', hero).addEventListener('click', function () { show(index + 1); restart(); });

        function slideFor(item, n) {
            const el = document.createElement('div');
            el.className = 'hero-slide s' + (n % 4 + 1);
            const copy = document.createElement('div'); copy.className = 'copy';
            const eyebrow = document.createElement('span'); eyebrow.className = 'eyebrow';
            eyebrow.textContent = item.discount ? 'Hot deal - ' + item.discount + '% off' : 'Top pick';
            const h2 = document.createElement('h2'); h2.textContent = item.name;
            const p = document.createElement('p'); p.textContent = item.brand + ' \u00b7 now only ' + item.price;
            const a = document.createElement('a'); a.className = 'btn btn-lg'; a.href = item.url; a.textContent = 'Shop now';
            copy.append(eyebrow, h2, p, a);
            const art = document.createElement('div'); art.className = 'art';
            const img = document.createElement('img'); img.src = item.image; img.alt = item.name;
            const bubble = document.createElement('span'); bubble.className = 'price-bubble'; bubble.textContent = item.price;
            art.append(img, bubble);
            el.append(copy, art);
            return el;
        }
        async function refreshHero() {
            try {
                const res = await fetch(ROOT + '/hero/feed');
                const data = await res.json();
                if (!data.items || !data.items.length) return;
                $$('.hero-slide', hero).slice(1).forEach(function (s) { s.remove(); });   // keep the welcome slide
                const anchor = $('.hero-nav.prev', hero);
                data.items.forEach(function (item, n) { hero.insertBefore(slideFor(item, n), anchor); });
                slides = $$('.hero-slide', hero);
                buildDots(); show(1); restart();
            } catch (err) { /* keep the current slides */ }
        }
        buildDots(); show(0); restart();
        if (REFRESH) setInterval(refreshHero, REFRESH);
    }

    /* ---------- flash-sale countdown ---------- */
    const cd = $('[data-countdown]');
    if (cd) {
        const end = new Date(cd.getAttribute('data-countdown')).getTime();
        const pad = function (n) { return String(n).padStart(2, '0'); };
        const tick = function () {
            let s = Math.max(0, Math.floor((end - Date.now()) / 1000));
            const h = Math.floor(s / 3600); s -= h * 3600;
            const m = Math.floor(s / 60); s -= m * 60;
            $('[data-h]', cd).textContent = pad(h);
            $('[data-m]', cd).textContent = pad(m);
            $('[data-s]', cd).textContent = pad(s);
        };
        tick(); setInterval(tick, 1000);
    }

    /* ---------- product gallery carousel (auto-advances) ---------- */
    const gallery = $('.gallery');
    if (gallery) {
        const slides = $$('.slide', gallery);
        const thumbs = $$('.gallery-thumbs button', gallery);
        const counter = $('.counter', gallery);
        const bar = $('.progress', gallery);
        const playBtn = $('.autoplay', gallery);
        const DELAY = parseInt(gallery.getAttribute('data-delay') || '30000', 10);
        let i = 0, timer = null, playing = slides.length > 1, started = 0;

        function show(n) {
            i = (n + slides.length) % slides.length;
            slides.forEach(function (s, k) { s.classList.toggle('active', k === i); });
            thumbs.forEach(function (t, k) { t.classList.toggle('active', k === i); });
            if (counter) counter.textContent = (i + 1) + ' / ' + slides.length;
            animateBar();
        }
        function animateBar() {
            if (!bar) return;
            bar.style.transition = 'none'; bar.style.width = '0';
            if (!playing) return;
            void bar.offsetWidth;
            bar.style.transition = 'width ' + DELAY + 'ms linear'; bar.style.width = '100%';
        }
        function play() {
            clearInterval(timer);
            if (!playing || slides.length < 2) return;
            timer = setInterval(function () { show(i + 1); }, DELAY);
            animateBar();
        }
        function stop() { clearInterval(timer); if (bar) { bar.style.transition = 'none'; bar.style.width = '0'; } }

        thumbs.forEach(function (t, k) { t.addEventListener('click', function () { show(k); play(); }); });
        const prev = $('.g-nav.prev', gallery), next = $('.g-nav.next', gallery);
        if (prev) prev.addEventListener('click', function () { show(i - 1); play(); });
        if (next) next.addEventListener('click', function () { show(i + 1); play(); });
        if (playBtn) playBtn.addEventListener('click', function () {
            playing = !playing;
            playBtn.innerHTML = playing ? '<i class="fa-solid fa-pause"></i>' : '<i class="fa-solid fa-play"></i>';
            playing ? play() : stop();
        });
        const main = $('.gallery-main', gallery);
        main.addEventListener('mouseenter', function () { if (playing) stop(); });
        main.addEventListener('mouseleave', function () { if (playing) play(); });
        if (slides.length < 2) {
            [prev, next, playBtn, counter].forEach(function (el) { if (el) el.classList.add('hidden'); });
        }
        show(0); play();
    }

    /* ---------- quantity stepper ---------- */
    $$('.qty-stepper').forEach(function (box) {
        const input = $('input', box);
        const max = parseInt(input.getAttribute('max') || '9999', 10);
        const minus = $('[data-dec]', box), plus = $('[data-inc]', box);
        const clamp = function (v) { return Math.min(Math.max(v || 1, 1), max); };
        minus.addEventListener('click', function () { input.value = clamp(parseInt(input.value, 10) - 1); });
        plus.addEventListener('click', function () { input.value = clamp(parseInt(input.value, 10) + 1); });
        input.addEventListener('change', function () { input.value = clamp(parseInt(input.value, 10)); });
    });

    /* ---------- cart: auto-submit when quantity typed ---------- */
    $$('[data-autosubmit]').forEach(function (el) {
        el.addEventListener('change', function () { el.form.submit(); });
    });

    /* ---------- image upload: previews + drag and drop ---------- */
    const upload = $('[data-upload]');
    if (upload) {
        const input = $('input[type=file]', upload);
        const grid = $('#upload-previews');
        const render = function () {
            grid.innerHTML = '';
            Array.from(input.files).forEach(function (f) {
                const url = URL.createObjectURL(f);
                const div = document.createElement('div');
                div.className = 'thumb';
                div.innerHTML = '<img alt=""><label>New</label>';
                div.querySelector('img').src = url;
                grid.appendChild(div);
            });
        };
        input.addEventListener('change', render);
        ['dragover', 'dragenter'].forEach(function (ev) {
            upload.addEventListener(ev, function (e) { e.preventDefault(); upload.classList.add('drag'); });
        });
        ['dragleave', 'drop'].forEach(function (ev) {
            upload.addEventListener(ev, function (e) { e.preventDefault(); upload.classList.remove('drag'); });
        });
        upload.addEventListener('drop', function (e) {
            if (e.dataTransfer && e.dataTransfer.files.length) { input.files = e.dataTransfer.files; render(); }
        });
    }

    /* ---------- endless explore feed ---------- */
    const feed = $('#feed');
    if (feed) {
        const seed = feed.getAttribute('data-seed');
        const btn = $('#feed-more');
        const sentinel = $('#feed-sentinel');
        let page = 1, loading = false, autoLoads = 0;
        const AUTO_LIMIT = 3;   // after this many automatic loads, show a "Load more" button

        async function load() {
            if (loading) return;
            loading = true; btn.disabled = true;
            btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Loading';
            try {
                const res = await fetch(ROOT + '/explore/feed?page=' + page + '&seed=' + encodeURIComponent(seed));
                const data = await res.json();
                feed.insertAdjacentHTML('beforeend', data.html);
                page = data.next;
            } catch (err) { /* ignore; user can press the button again */ }
            btn.disabled = false;
            btn.innerHTML = 'Load more products';
            loading = false;
        }
        btn.addEventListener('click', load);

        if ('IntersectionObserver' in window) {
            const obs = new IntersectionObserver(function (entries) {
                if (entries[0].isIntersecting && autoLoads < AUTO_LIMIT) {
                    autoLoads += 1;
                    load().then(function () { if (autoLoads >= AUTO_LIMIT) obs.disconnect(); });
                }
            }, { rootMargin: '400px' });
            obs.observe(sentinel);
        }
    }
    /* ---------- market news ---------- */
    const newsBox = $('#market-news');
    if (newsBox) {
        const tabs = $('.news-tabs', newsBox), grid = $('.news-grid', newsBox);
        const ago = function (ts) {
            if (!ts) return '';
            const h = Math.floor((Date.now() / 1000 - ts) / 3600);
            if (h < 1) return 'Just now';
            if (h < 24) return h + 'h ago';
            const d = Math.floor(h / 24);
            return d < 30 ? d + 'd ago' : new Date(ts * 1000).toLocaleDateString();
        };
        const fallbackIcon = function (icon) { return '<i class="fa-solid ' + icon + '"></i>'; };
        const show = function (topic) {
            grid.innerHTML = '';
            topic.items.forEach(function (it) {
                const a = document.createElement('a');
                a.className = 'news-card'; a.href = it.url; a.target = '_blank'; a.rel = 'noopener noreferrer';
                const pic = document.createElement('div'); pic.className = 'pic';
                if (it.image) {
                    pic.classList.add('loading');
                    const img = document.createElement('img'); img.alt = ''; img.loading = 'lazy';
                    let retried = false;
                    img.onload = function () { img.classList.add('loaded'); pic.classList.remove('loading'); };
                    img.onerror = function () {
                        if (!retried) { retried = true; setTimeout(function () { img.src = it.image + '&r=1'; }, 1500); return; }
                        pic.classList.remove('loading'); pic.innerHTML = fallbackIcon(topic.icon);
                    };
                    img.src = it.image;
                    pic.appendChild(img);
                } else { pic.innerHTML = fallbackIcon(topic.icon); }
                const txt = document.createElement('div'); txt.className = 'txt';
                const h3 = document.createElement('h3'); h3.textContent = it.title;
                const by = document.createElement('div'); by.className = 'by';
                const src = document.createElement('strong'); src.textContent = it.source || 'News';
                const when = document.createElement('span'); when.textContent = ago(it.published);
                by.append(src, when);
                txt.append(h3, by);
                a.append(pic, txt);
                grid.appendChild(a);
            });
        };
        const unavailable = function () {
            grid.innerHTML = '<p class="muted" style="padding:20px">News is unavailable right now. Please check back soon.</p>';
        };
        fetch(ROOT + '/news/feed').then(function (r) { return r.json(); }).then(function (data) {
            const topics = (data.topics || []).filter(function (t) { return t.items.length; });
            if (!topics.length) { unavailable(); return; }
            topics.forEach(function (t, n) {
                const b = document.createElement('button');
                b.type = 'button';
                b.innerHTML = fallbackIcon(t.icon) + ' ' + t.title;
                b.addEventListener('click', function () {
                    $$('button', tabs).forEach(function (x) { x.classList.remove('active'); });
                    b.classList.add('active'); show(t);
                });
                tabs.appendChild(b);
                if (n === 0) { b.classList.add('active'); show(t); }
            });
        }).catch(unavailable);
    }
    /* ---------- lazy-load shimmer for product thumbnails ---------- */
    function markLoaded(img) {
        const box = img.closest('.thumb');
        if (box) box.classList.add('loaded');
    }
    document.addEventListener('load', function (e) {
        if (e.target.tagName === 'IMG') markLoaded(e.target);
    }, true);
    document.addEventListener('error', function (e) {
        if (e.target.tagName === 'IMG') markLoaded(e.target);
    }, true);
    $$('.product-card .thumb img').forEach(function (img) { if (img.complete) markLoaded(img); });
    $$('.product-card .thumb').forEach(function (t) { if (!t.querySelector('img')) t.classList.add('loaded'); });

    /* ---------- profile picture chooser ---------- */
    const avatarInput = $('#avatar-file');
    if (avatarInput) {
        avatarInput.addEventListener('change', function () {
            $('#avatar-name').textContent = avatarInput.files.length ? avatarInput.files[0].name : 'No file chosen';
        });
    }
})();
