(() => {
  // T-080 baseline counter. Counts what is VISIBLE IN THE VIEWPORT at the current scroll position.
  const vh = innerHeight, vw = innerWidth, T = 'rgba(0, 0, 0, 0)';
  const cs = el => getComputedStyle(el);
  const vis = el => { const r = el.getBoundingClientRect(), s = cs(el);
    return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < vh && r.right > 0 && r.left < vw
      && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0; };
  const everything = [...document.body.querySelectorAll('*')];
  const all = everything.filter(vis);
  const hasText = el => [...el.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  const texts = all.filter(hasText);
  const tally = (els, key) => els.reduce((m, el) => { const k = key(el); if (k) m[k] = (m[k] || 0) + 1; return m; }, {});
  const typeKey = el => { const s = cs(el); return [s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), s.fontSize, s.fontWeight, s.fontStyle, s.textTransform].join(' | '); };
  const lineKinds = els => { const m = {}; els.forEach(el => { const s = cs(el);
    ['Top', 'Right', 'Bottom', 'Left'].forEach(side => { const w = parseFloat(s['border' + side + 'Width']), st = s['border' + side + 'Style'];
      const a = (s['border' + side + 'Color'].match(/[\d.]+/g) || []).map(Number);   // skip borders painted fully transparent
      if (w > 0 && st !== 'none' && st !== 'hidden' && !(a.length > 3 && a[3] === 0)) { const k = st + ' ' + w + 'px'; m[k] = (m[k] || 0) + 1; } }); }); return m; };
  const svgDashed = els => els.filter(el => el instanceof SVGElement && !['none', ''].includes(cs(el).strokeDasharray) && cs(el).stroke !== 'none').length;
  const svgPatternFill = els => els.filter(el => el instanceof SVGElement && /^url\(/.test(cs(el).fill)).length;
  const isPill = el => { const s = cs(el), r = el.getBoundingClientRect();
    return r.height >= 16 && r.height <= 44 && r.width > r.height * 1.3 && parseFloat(s.borderTopLeftRadius) >= r.height / 2 - 1
      && (s.backgroundColor !== T || parseFloat(s.borderTopWidth) > 0); };
  const pinned = all.filter(el => ['fixed', 'sticky'].includes(cs(el).position)).map(el => { const r = el.getBoundingClientRect();
    return { tag: el.tagName.toLowerCase(), cls: String(el.className).slice(0, 70), position: cs(el).position, top: Math.round(r.top),
      visibleHeight: Math.round(Math.min(r.bottom, vh) - Math.max(r.top, 0)), width: Math.round(r.width), text: el.innerText.slice(0, 50).replace(/\s+/g, ' ') }; });
  return JSON.stringify({
    url: location.pathname, viewport: [vw, vh], scrollY: Math.round(scrollY), pageHeight: document.documentElement.scrollHeight,
    inViewport: {
      textElements: texts.length,                                   // elements that directly hold text
      controls: all.filter(el => el.matches('a,button,input,select,textarea,[role=button],[role=tab],[role=switch]')).length,
      pictures: all.filter(el => el.matches('img,svg,video,canvas')).length,
      monoTextElements: texts.filter(el => /mono/i.test(cs(el).fontFamily.split(',')[0])).length,
      uppercaseTextElements: texts.filter(el => cs(el).textTransform === 'uppercase').length,
      pillsAndChips: all.filter(isPill).length,
      typeStyles: tally(texts, typeKey),                            // family | size | weight | style | transform
      textColours: tally(texts, el => cs(el).color),
      fillColours: tally(all, el => { const c = cs(el).backgroundColor; return c === T ? '' : c; }),
      lineKinds: lineKinds(all),                                    // border style + width, per side
      svgDashedStrokes: svgDashed(all), svgPatternFills: svgPatternFill(all),
      hatchedOrStriped: all.filter(el => /repeating-(linear|conic|radial)-gradient/.test(cs(el).backgroundImage)).length,
      gradients: all.filter(el => /gradient/.test(cs(el).backgroundImage)).length,
      pinned,                                                       // fixed/sticky elements and the height they occupy now
    },
    wholePage: { elements: everything.length, lineKinds: lineKinds(everything), svgDashedStrokes: svgDashed(everything), svgPatternFills: svgPatternFill(everything),
      hatchedOrStriped: everything.filter(el => /repeating-(linear|conic|radial)-gradient/.test(cs(el).backgroundImage)).length },
  });
})()
