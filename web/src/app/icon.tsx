import { ImageResponse } from "next/og";

import { PrismMarkSvg } from "@/lib/ogCard";

// The favicon: the mark on the stationery ground, drawn by the same path as
// PrismMark so the tab and the masthead never disagree.
export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    <div style={{ width: 32, height: 32, display: "flex", alignItems: "center", justifyContent: "center", background: "#f2f4ee" }}>
      <PrismMarkSvg size={26} ink="#141414" />
    </div>,
    size,
  );
}
