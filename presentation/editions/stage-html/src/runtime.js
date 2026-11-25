/* Stage deck runtime extensions.
   - fixed 1920x1080 stage scaled to the viewport (exact 1:1 at 1920x1080)
   - ?export=1 disables motion and exposes window.__exportGo(i) for capture
   - window.__auditFontSizes() returns the per-slide computed type audit
   - window.__deckReady flips true after fonts and images settle            */
(function () {
  var params = new URLSearchParams(location.search);
  var exportMode = params.has('export');

  function fitStage() {
    var s = Math.min(innerWidth / 1920, innerHeight / 1080);
    document.documentElement.style.setProperty('--stage-scale', String(s));
  }
  addEventListener('resize', fitStage, { passive: true });
  fitStage();

  window.__exportGo = function (index) {
    document.body.classList.add('export');
    if (window.__setLowPowerMode) window.__setLowPowerMode(true, { persist: false });
    if (typeof go === 'function') go(Number(index), { force: true });
    window.scrollTo(0, 0);
  };

  /* Visible text = text node with a rendered parent inside a slide.
     Chrome, display and hidden chrome are excluded from the copy budget. */
  window.__auditFontSizes = function () {
    var slides = Array.prototype.slice.call(document.querySelectorAll('.slide'));
    return slides.map(function (slide, index) {
      var isCover = slide.dataset.layout === 'SWISS-COVER-ASCII';
      var allowed = isCover ? [32, 120] : [32, 96];
      var sizeCounts = {};
      var badSizes = [];
      var families = {};
      var badFamilies = [];
      var words = 0;
      var copyWords = 0;
      var walker = document.createTreeWalker(slide, NodeFilter.SHOW_TEXT, null);
      var node;
      while ((node = walker.nextNode())) {
        var raw = node.textContent;
        if (!raw || !raw.trim()) continue;
        var el = node.parentElement;
        if (!el) continue;
        if (el.closest('#nav,#hint,#overview,#ppt-presenter,[aria-hidden="true"]')) continue;
        var cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') continue;
        if (!el.getClientRects().length) continue;
        var size = Math.round(parseFloat(cs.fontSize) * 100) / 100;
        sizeCounts[size] = (sizeCounts[size] || 0) + 1;
        var firstFamily = cs.fontFamily.split(',')[0].replace(/["']/g, '').trim();
        families[firstFamily] = (families[firstFamily] || 0) + 1;
        var text = raw.replace(/\s+/g, ' ').trim();
        var w = text ? text.split(' ').filter(Boolean).length : 0;
        words += w;
        var isChrome = !!el.closest('.st-chrome');
        var isDisplay = !!el.closest('.st-d,.st-cover');
        if (!isChrome && !isDisplay) copyWords += w;
        if (allowed.indexOf(size) === -1) {
          badSizes.push({ size: size, text: text.slice(0, 90), tag: el.tagName, cls: String(el.className).slice(0, 60) });
        }
        if (!/^(georgia|arial|courier new|times new roman|helvetica|courier|serif|sans-serif|monospace)$/i.test(firstFamily)) {
          badFamilies.push({ family: firstFamily, text: text.slice(0, 60) });
        }
      }
      var images = slide.querySelectorAll('img').length;
      var icons = slide.querySelectorAll('svg').length;
      var brokenImages = [];
      slide.querySelectorAll('img').forEach(function (img) {
        if (!(img.complete && img.naturalWidth > 0)) brokenImages.push(img.getAttribute('src'));
      });
      return {
        index: index + 1,
        id: slide.dataset.slideId || '',
        layout: slide.dataset.layout || '',
        sizes: Object.keys(sizeCounts).map(Number).sort(function (a, b) { return a - b; }),
        sizeCounts: sizeCounts,
        badSizes: badSizes,
        badFamilies: badFamilies,
        families: families,
        words: words,
        copyWords: copyWords,
        images: images,
        icons: icons,
        brokenImages: brokenImages
      };
    });
  };


  window.__auditLayout = function () {
    return Array.prototype.slice.call(document.querySelectorAll('.slide')).map(function (slide, index) {
      var stage = slide.querySelector('.stage');
      if (!stage) return { index: index + 1, id: slide.dataset.slideId || '', overflow: [], maxBottom: 0 };
      var sr = stage.getBoundingClientRect();
      var scale = sr.width / 1920;
      var bad = [];
      var maxBottom = 0;
      var safeBottom = 0;
      var safeNode = '';
      var inners = stage.querySelectorAll('*');
      for (var i = 0; i < inners.length; i++) {
        var el = inners[i];
        var cs = getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden' || Number(cs.opacity) === 0) continue;
        var r = el.getBoundingClientRect();
        if (r.width < 2 || r.height < 2) continue;
        if (el.closest('.st-bleed-tex')) continue;
        var left = Math.round((r.left - sr.left) / scale);
        var top = Math.round((r.top - sr.top) / scale);
        var right = Math.round((r.right - sr.left) / scale);
        var bottom = Math.round((r.bottom - sr.top) / scale);
        if (bottom > maxBottom) maxBottom = bottom;
        if (left < -2 || top < -2 || right > 1922 || bottom > 1080) {
          var cls = el.className ? String(el.className).split(' ').filter(Boolean).slice(0, 2).join('.') : '';
          bad.push({ tag: el.tagName, cls: cls, left: left, top: top, right: right, bottom: bottom,
            text: (el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 44) });
        }
      }
      /* content safe line: text, cards, figures; full-bleed panels and images excluded */
      for (var j = 0; j < inners.length; j++) {
        var node = inners[j];
        if (node.closest('.st-chrome')) continue;
        var directText = false;
        for (var c = 0; c < node.childNodes.length; c++) {
          if (node.childNodes[c].nodeType === 3 && node.childNodes[c].textContent.trim()) { directText = true; break; }
        }
        var isBlock = directText || node.matches('.st-card, figure, figcaption');
        if (!isBlock) continue;
        var ncs = getComputedStyle(node);
        if (ncs.display === 'none' || ncs.visibility === 'hidden' || Number(ncs.opacity) === 0) continue;
        var nr = node.getBoundingClientRect();
        if (nr.width < 2 || nr.height < 2) continue;
        var nBottom = Math.round((nr.bottom - sr.top) / scale);
        if (nBottom > safeBottom) {
          safeBottom = nBottom;
          safeNode = (node.className ? String(node.className).split(' ').filter(Boolean).slice(0, 2).join('.') : node.tagName) + ' "' + (node.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 38) + '"';
        }
      }
      return { index: index + 1, id: slide.dataset.slideId || '', maxBottom: maxBottom, safeBottom: safeBottom, safeNode: safeNode, overflow: bad.slice(0, 10), overflowCount: bad.length };
    });
  };

  window.__auditExternal = function () {
    return Array.prototype.slice.call(document.querySelectorAll('link[href],script[src],img[src]'))
      .map(function (el) { return el.getAttribute('href') || el.getAttribute('src'); })
      .filter(function (u) { return u && /^https?:/i.test(u); });
  };

  window.__deckReady = false;
  var fontsReady = document.fonts ? document.fonts.ready : Promise.resolve();
  var imagesReady = Promise.all(Array.prototype.map.call(document.images, function (img) {
    if (img.complete) return Promise.resolve();
    return new Promise(function (resolve) { img.onload = resolve; img.onerror = resolve; });
  }));
  Promise.all([fontsReady, imagesReady]).then(function () {
    setTimeout(function () { window.__deckReady = true; }, 200);
  });

  if (exportMode) {
    document.body.classList.add('export');
    if (window.__setLowPowerMode) window.__setLowPowerMode(true, { persist: false });
    var start = Math.max(1, Number(params.get('slide') || 1));
    var applyStart = function () { if (typeof go === 'function') go(start - 1, { force: true }); };
    if (document.readyState === 'complete') applyStart();
    else addEventListener('load', applyStart);
  }
})();
