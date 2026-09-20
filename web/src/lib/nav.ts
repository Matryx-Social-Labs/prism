// Did the reader arrive here from inside Prism? `document.referrer` cannot
// say (it is frozen at the document's first load, and a single-page app never
// reloads), so the layout notes the previous path on every client navigation.
// The story page's back bar reads it: a previous path means real `back()` —
// the list they left, at the place they left it — otherwise /feed.
const KEY = "prism.nav.prev.v1";

export function notePath(pathname: string): void {
  try {
    const cur = window.sessionStorage.getItem(`${KEY}:cur`);
    if (cur === pathname) return;
    if (cur) window.sessionStorage.setItem(KEY, cur);
    window.sessionStorage.setItem(`${KEY}:cur`, pathname);
  } catch {
    /* blocked storage: the back bar falls back to /feed */
  }
}

export function cameFromInside(): boolean {
  try {
    return !!window.sessionStorage.getItem(KEY) && window.history.length > 1;
  } catch {
    return false;
  }
}
