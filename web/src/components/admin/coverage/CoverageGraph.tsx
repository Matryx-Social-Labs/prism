"use client";

/**
 * The coverage network in 3D (founder decision V4, 2026-09-24): an outlet per
 * sphere, sized by the stories it reported and coloured by its language; a
 * line where two outlets reported the same story, fainter the fewer they
 * share. Loaded only when a founder opens it (next/dynamic on
 * /admin/coverage); the tables beside it carry every number it draws.
 *
 * Drag to turn, scroll to zoom. It turns slowly on its own unless the reader
 * asked for reduced motion.
 */

import { Html, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import { useEffect, useMemo, useRef, useState } from "react";
import * as THREE from "three";

import { layout, type Link } from "./layout";

export interface GraphOutlet {
  id: string;
  name: string;
  language: string;
  stories: number;
  /** A CSS colour, e.g. var(--viz-2); read from the page so it follows the theme. */
  color: string;
}

const LABELLED = 8;

/** A CSS variable's value where the element sits (three.js needs real colours). */
const resolve = (el: Element, css: string) => {
  const name = css.match(/var\((--[\w-]+)\)/)?.[1];
  return name ? getComputedStyle(el).getPropertyValue(name).trim() || "#888" : css;
};

export default function CoverageGraph({ outlets, links, label }: { outlets: GraphOutlet[]; links: Link[]; label: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [paint, setPaint] = useState<{ nodes: Record<string, string>; edge: string; bg: string } | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const [still, setStill] = useState(false);

  useEffect(() => {
    const el = box.current!;
    setPaint({
      nodes: Object.fromEntries([...new Set(outlets.map((o) => o.color))].map((c) => [c, resolve(el, c)])),
      edge: resolve(el, "var(--ink-3)"),
      bg: resolve(el, "var(--surface)"),
    });
    setStill(window.matchMedia("(prefers-reduced-motion: reduce)").matches);
  }, [outlets]);

  const at = useMemo(() => layout(outlets.map((o) => o.id), links), [outlets, links]);
  const most = Math.max(1, ...outlets.map((o) => o.stories));
  const named = new Set([...outlets].sort((a, b) => b.stories - a.stories).slice(0, LABELLED).map((o) => o.id));

  const edges = useMemo(() => {
    if (!paint) return null;
    const kept = links.filter((l) => at.has(l.a) && at.has(l.b));
    const strongest = Math.max(1, ...kept.map((l) => l.shared));
    const pos = new Float32Array(kept.length * 6);
    const col = new Float32Array(kept.length * 6);
    const faint = new THREE.Color(paint.bg);
    const ink = new THREE.Color(paint.edge);
    kept.forEach((l, i) => {
      pos.set([...at.get(l.a)!, ...at.get(l.b)!], i * 6);
      const c = faint.clone().lerp(ink, 0.2 + 0.8 * (Math.log1p(l.shared) / Math.log1p(strongest)));
      col.set([c.r, c.g, c.b, c.r, c.g, c.b], i * 6);
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    return g;
  }, [links, at, paint]);

  return (
    <div ref={box} role="img" aria-label={label} className="relative h-[420px] w-full cursor-grab active:cursor-grabbing sm:h-[520px]">
      {paint && edges && (
        <Canvas camera={{ position: [0, 0, 34], fov: 50 }} dpr={[1, 2]}>
          <ambientLight intensity={0.9} />
          <directionalLight position={[10, 14, 10]} intensity={0.9} />
          <lineSegments geometry={edges}>
            <lineBasicMaterial vertexColors />
          </lineSegments>
          {outlets.map((o) => {
            const p = at.get(o.id)!;
            const r = 0.3 + 0.9 * Math.sqrt(o.stories / most);
            return (
              <mesh key={o.id} position={p} onPointerOver={() => setHover(o.id)} onPointerOut={() => setHover((h) => (h === o.id ? null : h))}>
                <sphereGeometry args={[r, 24, 16]} />
                <meshStandardMaterial color={paint.nodes[o.color]} roughness={0.55} />
                {(named.has(o.id) || hover === o.id) && (
                  <Html center position={[0, r + 0.7, 0]} style={{ pointerEvents: "none" }}>
                    <span
                      className="whitespace-nowrap rounded-[4px] px-1.5 py-0.5 text-[11.5px]"
                      style={{ background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line)" }}
                    >
                      {o.name}
                      {hover === o.id && <span className="ml-1 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{o.stories}</span>}
                    </span>
                  </Html>
                )}
              </mesh>
            );
          })}
          <OrbitControls autoRotate={!still} autoRotateSpeed={0.35} enablePan={false} minDistance={8} maxDistance={70} />
        </Canvas>
      )}
    </div>
  );
}
