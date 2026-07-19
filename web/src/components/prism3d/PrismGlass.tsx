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
        {/* faint facet outline; the lighter stage does the real visibility
            work — transmission glass refracts the backdrop and silhouettes */}
        <Edges scale={1.002} threshold={20} color="#6b6258" />
      </mesh>
    </group>
  );
}

useGLTF.preload("/prism3d/prism.glb");
