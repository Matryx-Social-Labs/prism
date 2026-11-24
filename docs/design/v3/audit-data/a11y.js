(() => {
  // T-080 accessibility baseline for what is VISIBLE IN THE VIEWPORT: tap targets under 44 px and text under 4.5:1 (3:1 for large text).
  const vh = innerHeight, vw = innerWidth, cs = el => getComputedStyle(el);
  const vis = el => { const r = el.getBoundingClientRect(), s = cs(el);
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0; };
  // Any CSS colour syntax (rgb, color(srgb …), oklch, color-mix results) → sRGB 0-255 + alpha, by painting one canvas pixel.
  const ctx = Object.assign(document.createElement('canvas'), { width: 1, height: 1 }).getContext('2d', { willReadFrequently: true }), seen = {};
  const rgba = c => seen[c] || (seen[c] = (() => { ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = '#000'; ctx.fillStyle = c; ctx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data; return [r, g, b, a / 255]; })());   // getImageData is not premultiplied
  const over = (f, b) => [0, 1, 2].map(i => f[i] * f[3] + b[i] * (1 - f[3])).concat(1);
  const bgOf = el => { const stack = []; for (let n = el; n; n = n.parentElement) { const c = rgba(cs(n).backgroundColor); if (c[3] > 0) { stack.push(c); if (c[3] === 1) break; } }
    return stack.reverse().reduce((b, f) => over(f, b), [255, 255, 255, 1]); };
  const lum = c => { const [r, g, b] = c.slice(0, 3).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const label = el => (el.innerText || el.getAttribute('aria-label') || el.tagName).trim().replace(/\s+/g, ' ').slice(0, 40);
  const all = [...document.body.querySelectorAll('*')].filter(vis);
  const controls = all.filter(el => el.matches('a,button,input,select,textarea,[role=button],[role=tab],[role=switch]'));
  const small = controls.map(el => { const r = el.getBoundingClientRect(); return { label: label(el), w: Math.round(r.width), h: Math.round(r.height) }; }).filter(t => t.w < 44 || t.h < 44);
  const texts = all.filter(el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim()));
  const low = texts.map(el => { const s = cs(el), bg = bgOf(el), fg = over(rgba(s.color), bg), px = parseFloat(s.fontSize);
    const large = px >= 24 || (px >= 18.66 && +s.fontWeight >= 700); const hasImage = !!el.closest('[style*="background-image"]') ;
    return { text: label(el), px, ratio: +ratio(fg, bg).toFixed(2), need: large ? 3 : 4.5, overImage: hasImage }; }).filter(t => t.ratio < t.need);
  return JSON.stringify({ url: location.pathname, viewport: [vw, vh], controls: controls.length, targetsUnder44: small.length, targetsUnder44List: small.slice(0, 40),
    textElements: texts.length, textUnderAA: low.length, textUnderAAList: low.slice(0, 40), smallestTextPx: Math.min(...texts.map(el => parseFloat(cs(el).fontSize))),
    textUnder12px: texts.filter(el => parseFloat(cs(el).fontSize) < 12).length });
})()
