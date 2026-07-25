import { ImageResponse } from "next/og";

import { fetchEvent } from "@/lib/api";

// Social card for a shared /story/<id> link. Most stories carry no publisher
// photo (image_url is null well over half the time), and without this those
// shares land in WhatsApp as a bare text link. Stories that DO have a photo keep
// it — page.tsx sets openGraph.images and that wins over this file.
// Same constraints as the trending card: monochrome + spectrum accent (color
// means a lens is speaking; this bar is the brand mark), no LLM, Node runtime.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let title = "One story. Every perspective.";
  let sources = 0;
  let sector = "";
  try {
    const e = await fetchEvent(id);
    title = e.title;
    sources = e.sources?.length ?? 0;
    sector = e.sector ?? "";
  } catch {
    /* fall back to defaults */
  }

  const eyebrow = ["PRISM", sector.replaceAll("_", " "), sources ? `${sources} SOURCES` : ""]
    .filter(Boolean)
    .join(" · ")
    .toUpperCase();

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          background: "#ffffff",
          color: "#1a1a1a",
          padding: "64px 72px",
          fontFamily: "Georgia, serif",
        }}
      >
        {/* spectrum accent (brand mark) */}
        <div
          style={{
            height: 8,
            width: "100%",
            borderRadius: 4,
            background: "linear-gradient(90deg,#F59E0B,#06B6D4,#8B5CF6)",
          }}
        />
        <div
          style={{
            marginTop: 40,
            fontSize: 22,
            letterSpacing: 4,
            color: "#6b7280",
            fontFamily: "monospace",
            display: "flex",
          }}
        >
          {eyebrow}
        </div>
        <div style={{ marginTop: 28, fontSize: 58, lineHeight: 1.14, fontWeight: 600, display: "flex" }}>
          {title.length > 120 ? `${title.slice(0, 118)}…` : title}
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: 24, color: "#9ca3af", display: "flex" }}>One story. Every perspective.</div>
      </div>
    ),
    size,
  );
}
