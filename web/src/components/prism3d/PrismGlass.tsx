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
      {/* visible hi-res beveled prism.
          Tuned per drei MeshTransmissionMaterial guidance: samples+resolution
          for smooth (non-grainy) refraction, ior 1.6 for a real glass bend, and
          chromaticAberration held at ~0.45 so the glass fringes elegantly — the
          dramatic spectrum comes from the separate Rainbow (Snell's law), not a
          maxed-out material fringe. distortion adds a living, organic surface. */}
      <mesh position={[0, 0, 0.6]} renderOrder={10} scale={2} dispose={null} geometry={nodes.Cone.geometry}>
        <MeshTransmissionMaterial
          samples={12}
          resolution={512}
          transmission={1}
          clearcoat={1}
          clearcoatRoughness={0.04}
          thickness={1.15}
          ior={1.6}
          chromaticAberration={0.45}
          anisotropy={0.15}
          roughness={0}
          distortion={0.14}
          distortionScale={0.3}
          temporalDistortion={0.08}
          toneMapped={false}
        />
        {/* ONE soft facet line — enough to read the triangular silhouette on the
            black stage, without the hard double CAD-wireframe look it had before. */}
        <Edges scale={1.003} threshold={20} color="#5b6678" />
      </mesh>
    </group>
  );
}

useGLTF.preload("/prism3d/prism.glb");
