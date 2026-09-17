/**
 * A link that opens the source article scrolled to the quote, highlighted:
 * the URL fragment `#:~:text=` (Text Fragments — Chrome, Edge, Safari 16.4+,
 * Firefox 131+). A long quote is sent as its first and last few words
 * (`textStart,textEnd`), which survives the outlet's own line breaks and
 * the odd typographic quote; a short one goes whole. Browsers without the
 * feature simply open the article.
 */
export function quoteLink(url: string, quote: string): string {
  const words = quote.trim().split(/\s+/);
  const enc = (s: string) => encodeURIComponent(s).replace(/-/g, "%2D").replace(/,/g, "%2C");
  const frag = words.length > 12 ? `${enc(words.slice(0, 6).join(" "))},${enc(words.slice(-6).join(" "))}` : enc(words.join(" "));
  return `${url.split("#")[0]}#:~:text=${frag}`;
}
