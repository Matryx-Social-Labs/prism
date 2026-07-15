// design-sync shim: next/image -> plain <img> for the DS bundle.
// The app keeps real next/image; only the Claude Design bundle uses this.
import * as React from "react";

type Props = React.ImgHTMLAttributes<HTMLImageElement> & {
  fill?: boolean;
  priority?: boolean;
  sizes?: string;
};

export default function Image({ fill, priority: _priority, style, ...rest }: Props) {
  const fillStyle: React.CSSProperties = fill
    ? { position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover" }
    : {};
  // eslint-disable-next-line @next/next/no-img-element, jsx-a11y/alt-text
  return <img {...rest} style={{ ...fillStyle, ...style }} />;
}
