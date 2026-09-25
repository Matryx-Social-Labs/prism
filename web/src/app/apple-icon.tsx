import { ImageResponse } from "next/og";

import { PrismMarkSvg } from "@/lib/ogCard";

export const size = { width: 180, height: 180 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    <div style={{ width: 180, height: 180, display: "flex", alignItems: "center", justifyContent: "center", background: "#F7F6F2" }}>
      <PrismMarkSvg size={120} ink="#111317" />
    </div>,
    size,
  );
}
