import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { withDeckPage } from '../../custom-html/scripts/cdp.mjs';

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, '..');
const [deckPath, selector, outName] = process.argv.slice(2);

function paletteAudit(cfg) {
  const slides = Array.from(document.querySelectorAll(cfg.selector));
  const EXCLUDE = '.notes, [aria-hidden="true"], #nav, #hint, #overview, #ppt-presenter';
  const toHex = (value) => {
    if (!value) return null;
    if (value === 'transparent' || value === 'none') return null;
    let m = value.match(/^rgba?\(([^)]+)\)$/);
    if (m) {
      const parts = m[1].split(',').map((s) => parseFloat(s.trim()));
      const [r, g, b] = parts;
      const a = parts.length > 3 ? parts[3] : 1;
      if (a === 0) return null;
      return '#' + [r, g, b].map((v) => Math.round(v).toString(16).padStart(2, '0')).join('').toUpperCase();
    }
    m = value.match(/^#[0-9a-f]{3,8}$/i);
    if (m) {
      let h = value.slice(1).toUpperCase();
      if (h.length === 3) h = h.split('').map((c) => c + c).join('');
      return '#' + h.slice(0, 6);
    }
    return null;
  };
  const perSlide = slides.map((slide, index) => {
    const colors = {};
    const bump = (hex, prop) => {
      if (!hex) return;
      colors[hex] = colors[hex] || { count: 0, props: {} };
      colors[hex].count += 1;
      colors[hex].props[prop] = (colors[hex].props[prop] || 0) + 1;
    };
    for (const el of slide.querySelectorAll('*')) {
      if (el.closest(EXCLUDE)) continue;
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (r.width < 1 || r.height < 1) continue;
      bump(toHex(cs.color), 'color');
      bump(toHex(cs.backgroundColor), 'background');
      for (const side of ['Top', 'Right', 'Bottom', 'Left']) {
        if (parseFloat(cs['border' + side + 'Width']) > 0) bump(toHex(cs['border' + side + 'Color']), 'border');
      }
      if (el instanceof SVGElement) {
        bump(toHex(cs.fill), 'fill');
        bump(toHex(cs.stroke), 'stroke');
      }
    }
    return { index: index + 1, colors };
  });
  return { perSlide };
}
const expression = '(' + paletteAudit.toString() + ')(' + JSON.stringify({ selector }) + ')';
const data = await withDeckPage(deckPath, (page) => page.evaluate(expression));
mkdirSync(resolve(ROOT, 'audits'), { recursive: true });
writeFileSync(resolve(ROOT, 'audits', outName), JSON.stringify(data, null, 2));
const ALLOWED = new Set(['#FAFAFA', '#09090B', '#1447E6', '#E5E5E5', '#0A0A0A', '#171717', '#C10007', '#FFFFFF']);
const all = {};
for (const s of data.perSlide) for (const [hex, info] of Object.entries(s.colors)) {
  all[hex] = all[hex] || { count: 0, slides: new Set() };
  all[hex].count += info.count;
  all[hex].slides.add(s.index);
}
console.log('distinct colors:', Object.keys(all).length);
for (const [hex, info] of Object.entries(all).sort((a, b) => b[1].count - a[1].count)) {
  console.log((ALLOWED.has(hex) ? 'ALLOWED ' : 'EXTRA   ') + hex.padEnd(8), String(info.count).padStart(5), 'slides', Array.from(info.slides).join(','));
}
