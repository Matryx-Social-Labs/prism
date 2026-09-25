import type { MetadataRoute } from "next";

// Installable on a phone from the browser menu: the record as an app screen,
// opening on Today. Icons are the brand exports (design/logo/build.py).
export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Prism — Follow the story, not the headlines.",
    short_name: "Prism",
    description: "One live story record from monitored outlets, with every development, verified quote and source open to inspection.",
    start_url: "/feed",
    scope: "/",
    display: "standalone",
    background_color: "#F7F6F2",
    theme_color: "#F7F6F2",
    lang: "en-IN",
    categories: ["news"],
    icons: [
      { src: "/brand/prism-mark-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/brand/prism-app-icon-1024.png", sizes: "1024x1024", type: "image/png", purpose: "maskable" },
    ],
  };
}
