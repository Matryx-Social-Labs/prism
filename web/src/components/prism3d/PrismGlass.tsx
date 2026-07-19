"use client";

// Ported from pmndrs/examples demos/nextjs-prism (MIT) — src/components/Prism.jsx
// The beveled glass prism (GLTF) + an invisible low-res triangular proxy the
// Reflect raycaster hits (the ray handlers are plain object properties, which
// is what Reflect looks for — assigned via ref, since they aren't JSX props).

import { Edges, MeshTransmissionMaterial, useGLTF } from "@react-three/drei";
import type { Mesh, BufferGeometry } from "three";
import type { RayEvent, RayMesh } from "./Reflect";

export function PrismGlass({
  onRayOver,
  onRayOut,
  onRayMove,
  ...props
}: {
  position?: [number, number, number];
  onRayOver?: (e: RayEvent) => void;
  onRayOut?: (e: RayEvent) => void;
  onRayMove?: (e: RayEvent) => void;
}) {
  const { nodes } = useGLTF("/prism3d/prism.glb") as unknown as {
    nodes: { Cone: { geometry: BufferGeometry } };
  };
  return (
    <group {...props}>
      {/* invisible raycast target */}
      <mesh
        visible={false}
        scale={1.9}
        rotation={[Math.PI / 2, Math.PI, 0]}
        ref={(m: Mesh | null) => {
          if (m) Object.assign(m as RayMesh, { onRayOver, onRayOut, onRayMove });
        }}
      >
        <cylinderGeometry args={[1, 1, 1, 3, 1]} />
      </mesh>
      {/* luminous inner shell: a whisper of self-glow so the glass volume
          reads on the black stage without washing out the refraction */}
      <mesh position={[0, 0, 0.6]} scale={1.96} geometry={nodes.Cone.geometry}>
        <meshBasicMaterial color="#8fa3b8" transparent opacity={0.05} depthWrite={false} toneMapped={false} />
      </mesh>
      {/* visible hi-res beveled prism */}
      <mesh position={[0, 0, 0.6]} renderOrder={10} scale={2} dispose={null} geometry={nodes.Cone.geometry}>
        <MeshTransmissionMaterial
          clearcoat={1}
          transmission={1}
          thickness={0.9}
          roughness={0}
          anisotropy={0.1}
          chromaticAberration={1}
          toneMapped={false}
        />
        {/* faint facet outline so the glass reads as a prism even before
            the beam lights it (against the dark stage it was invisible) */}
        {/* facet edges: a cool bright line + soft outer halo so the prism's
            triangular form is unmistakable on black */}
        <Edges scale={1.002} threshold={20} color="#b8c4d4" />
        <Edges scale={1.01} threshold={20} color="#2e3644" />
      </mesh>
    </group>
  );
}

useGLTF.preload("/prism3d/prism.glb");
