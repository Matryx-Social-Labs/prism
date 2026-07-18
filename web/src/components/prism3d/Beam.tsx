"use client";

// Ported from pmndrs/examples demos/nextjs-prism (MIT) — src/components/Beam.jsx
// Renders the raycast polyline from Reflect as additive light streaks + glows.

import * as THREE from "three";
import { forwardRef, useImperativeHandle, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { useTexture } from "@react-three/drei";
import { Reflect, type ReflectApi } from "./Reflect";

export const Beam = forwardRef<
  ReflectApi,
  {
    children: React.ReactNode;
    position?: [number, number, number];
    stride?: number;
    width?: number;
    bounce?: number;
    far?: number;
  }
>(({ children, position, stride = 4, width = 8, ...props }, fRef) => {
  const streaks = useRef<THREE.InstancedMesh>(null);
  const glow = useRef<THREE.InstancedMesh>(null);
  const reflect = useRef<ReflectApi>(null);
  const [streakTexture, glowTexture] = useTexture([
    "/prism3d/lensflare/lensflare2.png",
    "/prism3d/lensflare/lensflare0_bw.jpg",
  ]);

  const obj = useMemo(() => new THREE.Object3D(), []);
  const f = useMemo(() => new THREE.Vector3(), []);
  const t = useMemo(() => new THREE.Vector3(), []);
  const n = useMemo(() => new THREE.Vector3(), []);
  const config = {
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
  };

  useFrame(() => {
    if (!reflect.current || !streaks.current || !glow.current) return;
    const range = reflect.current.update() - 1;

    for (let i = 0; i < range; i++) {
      f.fromArray(reflect.current.positions, i * 3);
      t.fromArray(reflect.current.positions, i * 3 + 3);
      n.subVectors(t, f).normalize();
      obj.position.addVectors(f, t).divideScalar(2);
      obj.scale.set(t.distanceTo(f) * stride, width, 1);
      obj.rotation.set(0, 0, Math.atan2(n.y, n.x));
      obj.updateMatrix();
      streaks.current.setMatrixAt(i, obj.matrix);
    }

    streaks.current.count = range;
    streaks.current.instanceMatrix.needsUpdate = true;

    obj.scale.setScalar(0);
    obj.updateMatrix();
    glow.current.setMatrixAt(0, obj.matrix);

    for (let i = 1; i < range; i++) {
      obj.position.fromArray(reflect.current.positions, i * 3);
      obj.scale.setScalar(0.75);
      obj.rotation.set(0, 0, 0);
      obj.updateMatrix();
      glow.current.setMatrixAt(i, obj.matrix);
    }

    glow.current.count = range;
    glow.current.instanceMatrix.needsUpdate = true;
  });

  useImperativeHandle(fRef, () => reflect.current!, []);

  return (
    <group position={position}>
      <Reflect {...props} ref={reflect}>
        {children}
      </Reflect>
      <instancedMesh ref={streaks} args={[undefined, undefined, 100]} instanceMatrix-usage={THREE.DynamicDrawUsage}>
        <planeGeometry />
        <meshBasicMaterial map={streakTexture} opacity={1.5} {...config} transparent={false} />
      </instancedMesh>
      <instancedMesh ref={glow} args={[undefined, undefined, 100]} instanceMatrix-usage={THREE.DynamicDrawUsage}>
        <planeGeometry />
        <meshBasicMaterial map={glowTexture} {...config} />
      </instancedMesh>
    </group>
  );
});
Beam.displayName = "Beam";
