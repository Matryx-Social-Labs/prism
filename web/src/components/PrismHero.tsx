"use client";

// The landing hero: a beam of light physically strikes a glass prism and
// splits into a spectrum — Prism's brand story, rendered for real.
// Scene architecture adapted from pmndrs/examples demos/nextjs-prism (MIT):
// raycast Beam → GLTF glass prism → Snell-angle Rainbow + Flare + Bloom.
// The beam follows the pointer over the stage; when idle it sweeps on its own.

import * as THREE from "three";
import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Bloom, BrightnessContrast, EffectComposer, Vignette } from "@react-three/postprocessing";
import { Beam } from "@/components/prism3d/Beam";
import { Flare } from "@/components/prism3d/Flare";
import { PrismGlass } from "@/components/prism3d/PrismGlass";
import { Rainbow, type RainbowMaterialImpl } from "@/components/prism3d/Rainbow";
import type { RayEvent } from "@/components/prism3d/Reflect";
import type { ReflectApi } from "@/components/prism3d/Reflect";
import { calculateRefractionAngle, lerp, lerpV3 } from "@/components/prism3d/util";

function FitZoom() {
  // Match the reference demo's ON-SCREEN prism presence (~40% of panel height —
  // its full-window canvas renders the prism ~260px; a small panel must zoom in).
  const camera = useThree((s) => s.camera);
  const height = useThree((s) => s.size.height);
  useEffect(() => {
    const ortho = camera as THREE.OrthographicCamera;
    ortho.zoom = height / 12;
    ortho.updateProjectionMatrix();
  }, [camera, height]);
  return null;
}

function Scene({ pointerActive }: { pointerActive: React.RefObject<boolean> }) {
  const [isPrismHit, hitPrism] = useState(false);
  const flare = useRef<THREE.Group>(null);
  const spot = useRef<THREE.SpotLight>(null);
  const boxreflect = useRef<ReflectApi>(null);
  const rainbow = useRef<THREE.Mesh>(null);
  const rayOrigin = useRef(new THREE.Vector3(-3, 1.2, 0));

  const rainbowMat = () => rainbow.current?.material as RainbowMaterialImpl | undefined;

  const rayOut = useCallback(() => hitPrism(false), []);
  const rayOver = useCallback((e: RayEvent) => {
    // Stop the ray at the prism, flash the spectrum on first contact
    e.stopPropagation();
    hitPrism(true);
    const mat = rainbowMat();
    if (mat) {
      mat.speed = 1;
      mat.emissiveIntensity = 12;
    }
  }, []);

  const vec = useRef(new THREE.Vector3()).current;
  const rayMove = useCallback(({ api, position, direction, normal }: RayEvent) => {
    if (!normal) return;
    // Extend the beam line to the prism's center
    vec.toArray(api.positions, api.number++ * 3);
    flare.current?.position.set(position.x, position.y, -0.5);
    flare.current?.rotation.set(0, 0, -Math.atan2(direction.x, direction.y));
    // Snell's law: rotate the rainbow to the refracted exit angle
    let angleScreenCenter = Math.atan2(-position.y, -position.x);
    const normalAngle = Math.atan2(normal.y, normal.x);
    const incidentAngle = angleScreenCenter - normalAngle;
    const refractionAngle = calculateRefractionAngle(incidentAngle) * 6;
    angleScreenCenter += refractionAngle;
    if (rainbow.current) rainbow.current.rotation.z = angleScreenCenter;
    if (spot.current) {
      lerpV3(spot.current.target.position, [Math.cos(angleScreenCenter), Math.sin(angleScreenCenter), 0], 0.05);
      spot.current.target.updateMatrixWorld();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useFrame((state) => {
    // Beam origin: pointer over the stage steers it; otherwise a slow sweep.
    const t = state.clock.elapsedTime;
    const target = new THREE.Vector3();
    if (pointerActive.current) {
      target.set((state.pointer.x * state.viewport.width) / 2, (state.pointer.y * state.viewport.height) / 2, 0);
    } else {
      target.set(
        -state.viewport.width * 0.46,
        Math.sin(t * 0.5) * 1.4 + 0.5,
        0
      );
    }
    rayOrigin.current.lerp(target, 0.08);
    boxreflect.current?.setRay([rayOrigin.current.x, rayOrigin.current.y, 0], [0, 0, 0]);

    // Settle the spectrum's intensity after the hit flash
    const mat = rainbowMat();
    if (mat) {
      lerp(mat as unknown as Record<string, number>, "emissiveIntensity", isPrismHit ? 1.6 : 0, 0.1);
      if (spot.current) spot.current.intensity = mat.emissiveIntensity;
    }
  });

  return (
    <>
      <ambientLight intensity={0.12} />
      {/* frontal key + cool rim: the facets carry a specular sheen and the
          silhouette separates from the black stage */}
      <pointLight position={[0, 0.5, 3.5]} intensity={0.7} decay={0} />
      <pointLight position={[1.5, 2.2, -2.5]} intensity={1.1} decay={0} color="#7d8ea8" />
      <pointLight position={[10, -10, 0]} intensity={0.12 * Math.PI} decay={0} />
      <pointLight position={[0, 10, 0]} intensity={0.12 * Math.PI} decay={0} />
      <pointLight position={[-10, 0, 0]} intensity={0.12 * Math.PI} decay={0} />
      <spotLight ref={spot} intensity={Math.PI} decay={0} distance={7} angle={1} penumbra={1} position={[0, 0, 1]} />
      <Beam ref={boxreflect} bounce={2} far={20}>
        <PrismGlass position={[0, -0.3, 0]} onRayOver={rayOver} onRayOut={rayOut} onRayMove={rayMove} />
      </Beam>
      <Rainbow ref={rainbow} startRadius={0} endRadius={0.5} fade={0} />
      <Flare ref={flare} visible={isPrismHit} renderOrder={10} scale={1.25} streak={[12.5, 20, 1]} />
    </>
  );
}

export default function PrismHero() {
  const wrapper = useRef<HTMLDivElement>(null);
  const pointerActive = useRef(false);
  const [visible, setVisible] = useState(true);

  // Don't burn GPU when the hero is scrolled out of view.
  useEffect(() => {
    const node = wrapper.current;
    if (!node) return;
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { threshold: 0.05 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  return (
    <div
      ref={wrapper}
      className="relative h-[340px] w-full overflow-hidden rounded-[22px] border sm:h-[400px]"
      style={{ borderColor: "var(--line)", background: "#0b0a09" }}
      onPointerEnter={() => (pointerActive.current = true)}
      onPointerLeave={() => (pointerActive.current = false)}
      aria-label="One story refracted into many perspectives"
      role="img"
    >
      <Canvas
        orthographic
        frameloop={visible ? "always" : "never"}
        gl={{ antialias: false }}
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 100], zoom: 30 }}
      >
        <color attach="background" args={["#0b0a09"]} />
        <FitZoom />
        <Suspense fallback={null}>
          <Scene pointerActive={pointerActive} />
          <EffectComposer>
            <Bloom mipmapBlur levels={8} intensity={0.9} luminanceThreshold={1} luminanceSmoothing={1} />
            {/* the reference grades with a proprietary LUT (not redistributable);
                a contrast crush + vignette approximates its deep-black stage */}
            <BrightnessContrast brightness={-0.05} contrast={0.22} />
            <Vignette eskil={false} offset={0.18} darkness={0.65} />
          </EffectComposer>
        </Suspense>
      </Canvas>
      {/* the design figure's captions, carried into 3D — no lens is named */}
      <span className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-[11px]" style={{ color: "#8d867d" }}>
        one story
      </span>
      <span className="pointer-events-none absolute bottom-4 right-4 text-[11px]" style={{ color: "#8d867d" }}>
        every perspective
      </span>
    </div>
  );
}
