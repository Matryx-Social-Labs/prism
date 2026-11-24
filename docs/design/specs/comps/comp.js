/* T-047 comp chrome: theme, banner, icon sprite, shell. Contract at the top of comp.css.
   Data: pages that need records include <script src="data.js"></script> before this file and
   read window.COMP_DATA (works from file://, where fetch does not). */
(function () {
  var theme = new URLSearchParams(location.search).get("theme");
  if (theme === "dark" || theme === "light") document.documentElement.dataset.theme = theme;

  var BANNER = "COMP · T-047 · real records from the public API, pulled 2026-11-24 17:50 UTC · anything tagged ILLUSTRATION is drawn, not data · not the product";
  var DATELINE = "Tue 24 Nov";

  // Path data copied from web/src/components/icons.tsx; the <g> carries each icon's stroke width.
  var NAV = '<g stroke-width="1.8">', END = "</g>";
  var ICONS = {
    "i-today": NAV + '<rect x="3" y="4" width="18" height="17" rx="3"/><path d="M3 9h18M8 2v4M16 2v4"/>' + END,
    "i-stories": NAV + '<path d="M4 19V5M4 12h7M4 5h11M11 12l4-3M15 5l5 3"/><circle cx="20" cy="8" r="1.5" fill="currentColor" stroke="none"/><circle cx="15" cy="9" r="1.5" fill="currentColor" stroke="none"/>' + END,
    "i-search": NAV + '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>' + END,
    "i-following": NAV + '<path d="M4 16l5-5 4 4 7-8"/><path d="M15 7h5v5"/>' + END,
    "i-you": NAV + '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>' + END,
    "i-bell": NAV + '<path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 21a2 2 0 0 0 4 0"/>' + END,
    "i-share": NAV + '<path d="M12 15V4M7 9l5-5 5 5M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5"/>' + END,
    "i-check": '<g stroke-width="2.5"><path d="m5 12 4 4L19 6"/></g>',
    "i-lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "i-arrow-right": '<path d="M5 12h14M13 6l6 6-6 6"/>',
    "i-arrow-left": '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    "i-arrow-up-right": '<path d="M7 17L17 7M9 7h8v8"/>',
    "i-chevron-down": '<path d="M6 9l6 6 6-6"/>',
    "i-close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "i-info": NAV + '<circle cx="12" cy="12" r="9"/><path d="M12 11v5"/><circle cx="12" cy="7.8" r="1" fill="currentColor" stroke="none"/>' + END,
    "i-speech": '<path d="M4 5h16v11H9l-5 4z"/>',
    "i-dash": '<path d="M5 12h14"/>',
    "i-play": '<g fill="currentColor" stroke="none"><path d="M7 4.5v15l12-7.5z"/></g>',
    "i-headphones": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><path d="M4 14h3v6H5a1 1 0 0 1-1-1zM20 14h-3v6h2a1 1 0 0 0 1-1z"/>',
    // The mark (web/src/lib/mark.ts): triangle in currentColor on its spectrum band.
    "i-mark": '<path d="M12 2.18 L22 19.5 L2 19.5 Z" fill="currentColor" stroke="none"/><rect x="2" y="19.5" width="20" height="2.75" fill="url(#comp-spectrum)" stroke="none"/>',
  };

  var DESTS = [
    { id: "today", label: "Today", icon: "i-today" },
    { id: "stories", label: "Stories", icon: "i-stories" },
    { id: "search", label: "Search", icon: "i-search" },
    { id: "following", label: "Following", icon: "i-following" },
    { id: "you", label: "You", icon: "i-you" },
  ];

  function ico(id, cls) { return '<svg class="ico' + (cls ? " " + cls : "") + '" aria-hidden="true"><use href="#' + id + '"/></svg>'; }
  function mark() { return '<svg class="comp-mark" viewBox="0 0 24 24" aria-hidden="true"><use href="#i-mark"/></svg>'; }
  function lockup(size) {
    return '<a class="comp-lockup" href="#" style="--mark:' + size + 'px">' + mark() +
      '<span class="comp-lockup__word"><span class="comp-lockup__q">read</span>Prism<span class="comp-lockup__q">.news</span></span></a>';
  }

  document.addEventListener("DOMContentLoaded", function () {
    var body = document.body;
    var current = body.dataset.current || "";
    var count = body.dataset.followingCount;
    if (!body.dataset.chrome) body.dataset.chrome = "app";
    function cur(id) { return id === current ? ' aria-current="page"' : ""; }
    function badge(id) { return id === "following" && count ? '<span class="comp-badge">' + count + "</span>" : ""; }

    var sprite = '<svg class="comp-sprite" aria-hidden="true" focusable="false"><defs>' +
      '<linearGradient id="comp-spectrum" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ef4444"/><stop offset="0.3333" stop-color="#f59e0b"/><stop offset="0.6667" stop-color="#06b6d4"/><stop offset="1" stop-color="#8b5cf6"/></linearGradient>' +
      Object.keys(ICONS).map(function (id) { return '<symbol id="' + id + '" viewBox="0 0 24 24">' + ICONS[id] + "</symbol>"; }).join("") +
      "</defs></svg>";

    var rail = '<nav class="comp-rail" aria-label="Primary"><a class="comp-rail__mark" href="#" aria-label="readPrism.news, Today">' + mark() + "</a>" +
      DESTS.map(function (d) {
        return '<a class="comp-rail__item" href="#"' + cur(d.id) + '><span class="comp-rail__pill">' + ico(d.icon) + badge(d.id) +
          '</span><span class="comp-rail__label">' + d.label + "</span></a>";
      }).join("") + "</nav>";

    var tabs = '<nav class="comp-tabs glass" aria-label="Primary">' +
      DESTS.map(function (d) { return '<a href="#"' + cur(d.id) + ">" + ico(d.icon, "ico--22") + d.label + "</a>"; }).join("") + "</nav>";

    var topbar = '<header class="comp-topbar glass">' + lockup(24) +
      '<nav class="comp-topbar__links" aria-label="Primary">' +
      DESTS.filter(function (d) { return d.id === "today" || d.id === "stories" || d.id === "following"; })
        .map(function (d) { return '<a href="#"' + cur(d.id) + ">" + d.label + badge(d.id) + "</a>"; }).join("") +
      '</nav><form class="comp-search" role="search" onsubmit="return false">' + ico("i-search") +
      '<input class="p-input" type="search" aria-label="Search" placeholder="Search stories, people, places"></form>' +
      '<a class="p-btn p-btn--text" href="#">Sign in</a></header>';

    body.insertAdjacentHTML("afterbegin",
      '<div class="comp-banner" role="note">' + BANNER + "</div>" +
      '<a class="comp-skip p-btn p-btn--primary p-btn--sm" href="#main">Skip to content</a>' + sprite +
      '<header class="comp-masthead glass">' + lockup(20) + '<span class="comp-dateline">' + DATELINE + "</span></header>" +
      '<header class="comp-backbar glass"><a class="p-iconbtn" href="#" aria-label="Back to Today">' + ico("i-arrow-left") + "</a>" + lockup(20) + "</header>" +
      '<header class="comp-barebar glass">' + lockup(22) + "</header>" + rail + topbar);
    body.insertAdjacentHTML("beforeend", tabs);
  });
})();
