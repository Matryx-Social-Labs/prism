# 05 · Navigation at each size class

Built by T-042, from the screens T-083 draws. This spec says which destinations exist, in what order, and
what must be reachable at each width. It does not say how any of it is drawn.

## Purpose

A reader can get to the same five places from any page at any width, in the same order, under the same
names. Today a tablet gets the phone's navigation stretched, and two destinations (Pulse, Watchlist) are in
different places on a phone and on a desk.

## Where it appears

On every reader page. Which navigation a page carries depends on the kind of page (see "Kinds of page").

## Content, in order

The five destinations, always in this order (D-20):

1. `Today` — the edition and everything reported today (`/feed`).
2. `Stories` — running stories (`/trending`).
3. `Search` (`/search`).
4. `Following` — what the reader follows; tickers, sectors and Market Pulse live under it (`/following`;
   spec 02).
5. `You` — the profile, languages, notifications, the account (`/you`).

Beside them, on every page: the wordmark, which leads to `Today`; and a skip link, first in the page.

### What each size class must provide

| Size class | Width | Must provide |
|---|---|---|
| Compact | < 600 | All five, each one press away, each with its name visible. |
| Medium | 600–1023 | All five, each one press away, each with its name visible. This tier gets a form of its own: it is not the compact form stretched and not the expanded form squeezed. |
| Expanded and up | ≥ 1024 | All five, each one press away. `Search` may be the search field itself rather than a link to it, and `You` may be the reader's avatar or `Sign in` — they are still the same two destinations, in the same order. |

Width alone decides the size class; height is not consulted, so a phone held sideways is medium.

### Kinds of page

A route declares which kind it is (T-042 replaces today's lists of route prefixes with this declaration):

| Kind | Navigation it carries | Routes |
|---|---|---|
| `app` | the five | Today, Stories, Search, Following, You and their sections |
| `record` | a way back, named for where it goes (`Back to Stories`), and the five | a record, a story, a quote, a person or subject page, Sources, legal, Corrections |
| `bare` | the wordmark only | onboarding, sign-in |
| `own` | the page provides its own | the landing and `/about`, `/plus`, the labeller, the admin |

## States

| State | What the reader is given / what happens |
|---|---|
| Empty · At the free limit | Do not apply: navigation is never empty and nothing in it is metered. |
| Loading a destination | Navigation does not change. The pressed destination becomes current at once; the page's own loading state shows in the content. |
| Error (offline, or the service unreachable) | Navigation stays and works; the page's own error state shows in the content. Navigation adds no message of its own. |
| Signed out | Identical. `You` opens the signed-out You page, where `Sign in` is; where `You` is shown as an avatar, it is shown as `Sign in`. |
| Current destination | Exactly one destination is marked current on an `app` page, in a way that does not depend on colour alone. |
| On a `record` page | The destination the reader came through stays marked (a record opened from Today keeps `Today`). Reached from outside — a shared link, a search engine, a reload with no history — none is marked. |
| Followed stories have moved | `Following` carries the number of followed stories with something new, as a number (`9+` above nine), never as a bare mark. No other destination ever carries a count. |
| The reader has not agreed to Prism remembering what they read (spec 02) | `Following` carries no number: there is nothing to count. |
| Before T-050 ships Following | The fourth destination is already named `Following`, opens today's `/watchlist`, and carries no number. |
| The width crosses 600 or 1024 (resize, rotation) | The form changes; the reader's scroll position in the content is kept. |
| A panel that blocks the page is open | Navigation cannot be reached or focused until it closes. |
| Printing | No navigation. |

## Copy

| Where | String |
|---|---|
| The five | `Today` · `Stories` · `Search` · `Following` · `You` |
| The navigation's accessible name | `Primary` |
| The wordmark's link | its visible text; it leads to `Today` |
| Skip link | `Skip to the content` |
| The search field, where Search is a field | placeholder `Search stories, people, places` |
| `Following` with a number, for assistive technology | `Following, {k} stories moved` · `Following, 1 story moved` |
| The way back on a `record` page | `Back to {destination}` — `Back to Today`, `Back to Stories`, `Back to Search`, `Back to Following`; with no history, `Back to Today` |

The names do not change with width, are never abbreviated, and are never replaced by a symbol alone.
`Watchlist` and `Pulse` are no longer destinations.

## Rules

1. Five destinations, one order, one set of names, at every width (D-20).
2. Every destination shows its name at every width. A symbol may accompany a name; it never replaces it.
3. Navigation holds the five and the wordmark, and nothing else: no theme control, no link to Plus, no
   sign-in beside `You`. Those live on the pages they belong to.
4. From any `app` or `record` page the five are reachable (PLAN §4.2: a leaf page keeps the global
   navigation). On a compact `record` page they may sit one press further away than on an `app` page, so that
   the page's own actions (a story's Ask and Share) are not crowded out — but they are never absent, and the
   way back is always present. T-083 draws how.
5. A page's own fixed actions and the navigation never overlap, and never together hide the control that has
   focus.
6. Only `Following` carries a count, and the count is a number.
7. Navigation never moves the reader on its own: no redirect on resize, no auto-advance.
8. The medium tier (600–1023) is designed for itself. Whether its content is one reading column or more is
   T-083's decision; that prose never runs wider than the reading measure is a standing rule of the product.

## Accessibility behaviour

- One navigation landmark, named `Primary`, is exposed at a time. A form of the navigation that is not shown
  at the current width is removed from the accessibility tree, not merely moved off screen.
- The skip link is first in the page; navigation comes before the content.
- The current destination has `aria-current="page"` on its own page, and `aria-current="true"` when it is
  marked only because the reader came through it.
- The link's accessible name carries the true count (`Following, 12 stories moved`); a visible `9+` is hidden
  from assistive technology.
- Every destination is a link reachable by keyboard in the fixed order, with a visible focus indication that
  nothing clips or covers.

## Needs from the API

| Needs | From |
|---|---|
| The number of followed stories with something new, for signed-in and signed-out readers | T-035 |
| The Following destination and its address | T-050 (spec 02) |
| Each route's declared kind | T-042 |
| How each form is drawn at each size class | T-083, then T-042 builds it |

## Decided here

1. **The same five in the same order everywhere**, with Pulse and the old Watchlist under `Following`. A
   reader who learns the product on a phone finds the same places on a desk.
2. **Names always.** A destination known only by a symbol is meaning without a word, and a first-time reader
   has no key.
3. **Nothing else lives in navigation.** Every extra item there is on every page; the default answer to
   "should this be here?" is no.
4. **A leaf page keeps the five**, on a phone too. Today a phone reader on a story has only a way back; PLAN
   §4.2 asks for global navigation on leaf pages, and a reader who arrived from a shared link has nowhere to
   go back to.
5. **The count on `Following` is a number**, and it is the only count in navigation.
6. **Width alone decides.** A sideways phone is a short, wide screen and gets the medium form.

## References

`~/prism-program/design-refs/tablet-shell.md`; design audit §7.2 "Tablet / desktop shell" (`board.md` rows
L1, L3, L4; L5 and L6 are from memory, not Mobbin — Mobbin holds no tablet screens).
