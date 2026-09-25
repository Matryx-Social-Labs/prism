"use client";

import { useEffect, useRef, useState } from "react";

/**
 * A publisher's photograph that fades in over its sunken placeholder as it loads
 * (Design System v2 · Motion, "Photo load": 320ms fade; the credit already sits on
 * the placeholder). A photo already in the cache is shown at once. Reduced motion
 * is handled by the global CSS (.photo-fade has no transition then).
 */
export function PhotoImg({ src, alt, eager = false, className = "", onError }: { src: string; alt: string; eager?: boolean; className?: string; onError?: () => void }) {
  const ref = useRef<HTMLImageElement>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (ref.current?.complete && ref.current.naturalWidth > 0) setReady(true);
  }, [src]);
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      ref={ref}
      src={src}
      alt={alt}
      loading={eager ? "eager" : "lazy"}
      decoding="async"
      referrerPolicy="no-referrer"
      onLoad={() => setReady(true)}
      onError={onError}
      className={`photo-fade h-full w-full object-cover ${ready ? "is-ready" : ""} ${className}`}
    />
  );
}
