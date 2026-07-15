"use client";

// Realistic glass prism: MeshTransmissionMaterial with chromatic dispersion,
// lit by spectrum-colored lightformers (no external HDR — fully offline).
// Loaded lazily via next/dynamic only for motion-ok, WebGL-capable clients.

import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Lightformer, MeshTransmissionMaterial } from "@react-three/drei";
import { useRef } from "react";
import type { Mesh } from "three";

function Prism() {
  const mesh = useRef<Mesh>(null);
  useFrame((state, delta) => {
    if (!mesh.current) return;
    mesh.current.rotation.y += delta * 0.25;
    mesh.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.3) * 0.12;
  });
  return (
    <mesh ref={mesh} rotation={[0.1, 0.4, 0]}>
      {/* 3 radial segments = triangular prism */}
      <cylinderGeometry args={[1.15, 1.15, 1.5, 3, 1]} />
      <MeshTransmissionMaterial
        transmission={1}
        thickness={0.9}
        roughness={0.07}
        ior={1.5}
        chromaticAberration={0.55}
        anisotropicBlur={0.2}
        samples={6}
        resolution={256}
        backside
      />
    </mesh>
  );
}

export default function PrismHero() {
  return (
    <div className="relative mx-auto mt-6 h-64 max-w-xl sm:h-80" aria-hidden>
      {/* the spectrum beams stay 2D behind the glass — they tell the story */}
      <svg viewBox="0 0 560 150" className="absolute inset-x-0 top-1/2 w-full -translate-y-1/2" style={{ opacity: 0.85 }}>
        <defs>
          <linearGradient id="beamW3d" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.9" />
          </linearGradient>
        </defs>
        <line x1="0" y1="75" x2="215" y2="75" stroke="url(#beamW3d)" strokeWidth="2.5" className="beam-in" />
        <line x1="345" y1="70" x2="560" y2="22" stroke="#f59e0b" strokeWidth="2.5" className="beam-out" opacity="0.9" />
        <line x1="345" y1="78" x2="560" y2="78" stroke="#06b6d4" strokeWidth="2.5" className="beam-out" opacity="0.9" />
        <line x1="345" y1="86" x2="560" y2="134" stroke="#8b5cf6" strokeWidth="2.5" className="beam-out" opacity="0.9" />
      </svg>
      <Canvas dpr={[1, 1.5]} camera={{ position: [0, 0, 4.6], fov: 40 }} gl={{ alpha: true, antialias: true }}>
        <Prism />
        <Environment resolution={64}>
          {/* spectrum light: what the glass refracts */}
          <Lightformer intensity={4} position={[0, 2.5, -2]} scale={[8, 2, 1]} color="#ffffff" />
          <Lightformer intensity={2.5} position={[-4, 0, 2]} scale={[3, 6, 1]} color="#f59e0b" />
          <Lightformer intensity={2.5} position={[4, 1, 2]} scale={[3, 6, 1]} color="#06b6d4" />
          <Lightformer intensity={2.2} position={[0, -3, 3]} scale={[6, 2, 1]} color="#8b5cf6" />
        </Environment>
      </Canvas>
    </div>
  );
}
