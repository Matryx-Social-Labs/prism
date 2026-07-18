"use client";

// Ported from pmndrs/examples demos/nextjs-prism (MIT) — src/components/Reflect.jsx
// A screen-space raycaster: traces a ray through the children, reflecting off
// meshes that carry onRayOver/onRayOut/onRayMove handlers, and exposes the
// polyline of hit points for the Beam to render.

import * as THREE from "three";
import { forwardRef, useImperativeHandle, useLayoutEffect, useMemo, useRef } from "react";
import { invalidate } from "@react-three/fiber";

export interface RayEvent {
  api: ReflectApi;
  object: THREE.Object3D;
  position: THREE.Vector3;
  direction: THREE.Vector3;
  reflect?: THREE.Vector3;
  normal?: THREE.Vector3;
  stopPropagation: () => void;
}

export type RayMesh = THREE.Mesh & {
  onRayOver?: (e: RayEvent) => void;
  onRayOut?: (e: RayEvent) => void;
  onRayMove?: (e: RayEvent) => void;
};

interface Hit {
  key: string;
  intersect: RayIntersection;
  stopped: boolean;
}

type RayIntersection = THREE.Intersection & {
  direction?: THREE.Vector3;
  reflect?: THREE.Vector3;
};

export interface ReflectApi {
  number: number;
  objects: THREE.Object3D[];
  hits: Map<string, Hit>;
  start: THREE.Vector3;
  end: THREE.Vector3;
  raycaster: THREE.Raycaster;
  positions: Float32Array;
  setRay: (start?: [number, number, number], end?: [number, number, number]) => void;
  update: () => number;
}

function isRayMesh(object: THREE.Object3D): object is RayMesh {
  const m = object as RayMesh;
  return (object as THREE.Mesh).isMesh && Boolean(m.onRayOver || m.onRayOut || m.onRayMove);
}

function createEvent(api: ReflectApi, hit: Hit, intersect: RayIntersection): RayEvent {
  return {
    api,
    object: intersect.object,
    position: intersect.point,
    direction: intersect.direction ?? new THREE.Vector3(),
    reflect: intersect.reflect,
    normal: intersect.face?.normal,
    stopPropagation: () => {
      hit.stopped = true;
    },
  };
}

export const Reflect = forwardRef<
  ReflectApi,
  {
    children: React.ReactNode;
    start?: [number, number, number];
    end?: [number, number, number];
    bounce?: number;
    far?: number;
  }
>(({ children, start: _start = [0, 0, 0], end: _end = [0, 0, 0], bounce = 10, far = 100 }, fRef) => {
  const maxBounce = (bounce || 1) + 1;

  const scene = useRef<THREE.Group>(null);
  const vStart = useMemo(() => new THREE.Vector3(), []);
  const vEnd = useMemo(() => new THREE.Vector3(), []);
  const vDir = useMemo(() => new THREE.Vector3(), []);
  const vPos = useMemo(() => new THREE.Vector3(), []);

  const api = useMemo<ReflectApi>(() => {
    let intersect: RayIntersection | undefined;
    let intersects: RayIntersection[] = [];
    const self: ReflectApi = {
      number: 0,
      objects: [],
      hits: new Map(),
      start: new THREE.Vector3(),
      end: new THREE.Vector3(),
      raycaster: new THREE.Raycaster(),
      positions: new Float32Array(Array.from({ length: (maxBounce + 10) * 3 }, () => 0)),
      setRay: (s = [0, 0, 0], e = [0, 0, 0]) => {
        self.start.set(...s);
        self.end.set(...e);
      },
      update: () => {
        self.number = 0;
        intersects = [];

        vStart.copy(self.start);
        vEnd.copy(self.end);
        vDir.subVectors(vEnd, vStart).normalize();
        vStart.toArray(self.positions, self.number++ * 3);

        while (true) {
          self.raycaster.set(vStart, vDir);
          intersect = self.raycaster.intersectObjects(self.objects, false)[0] as RayIntersection | undefined;
          if (self.number < maxBounce && intersect && intersect.face) {
            intersects.push(intersect);
            intersect.direction = vDir.clone();
            intersect.point.toArray(self.positions, self.number++ * 3);
            vDir.reflect(
              intersect.object
                .localToWorld(intersect.face.normal.clone())
                .sub(intersect.object.getWorldPosition(vPos))
                .normalize()
            );
            intersect.reflect = vDir.clone();
            vStart.copy(intersect.point);
          } else {
            vEnd.addVectors(vStart, vDir.multiplyScalar(far)).toArray(self.positions, self.number++ * 3);
            break;
          }
        }

        self.number = 1;
        self.hits.forEach((hit) => {
          if (!intersects.find((i) => i.object.uuid === hit.key)) {
            self.hits.delete(hit.key);
            const obj = hit.intersect.object as RayMesh;
            if (obj.onRayOut) {
              invalidate();
              obj.onRayOut(createEvent(self, hit, hit.intersect));
            }
          }
        });

        for (intersect of intersects) {
          self.number++;
          if (!self.hits.has(intersect.object.uuid)) {
            const hit: Hit = { key: intersect.object.uuid, intersect, stopped: false };
            self.hits.set(intersect.object.uuid, hit);
            const obj = intersect.object as RayMesh;
            if (obj.onRayOver) {
              invalidate();
              obj.onRayOver(createEvent(self, hit, intersect));
            }
          }

          const hit = self.hits.get(intersect.object.uuid)!;
          const obj = intersect.object as RayMesh;
          if (obj.onRayMove) {
            invalidate();
            obj.onRayMove(createEvent(self, hit, intersect));
          }

          if (hit.stopped) break;
          if (intersect === intersects[intersects.length - 1]) self.number++;
        }
        return Math.max(2, self.number);
      },
    };
    return self;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [maxBounce, far]);

  useLayoutEffect(() => void api.setRay(_start, _end), [api, _start, _end]);
  useImperativeHandle(fRef, () => api, [api]);

  useLayoutEffect(() => {
    api.objects = [];
    scene.current?.traverse((object) => {
      if (isRayMesh(object)) api.objects.push(object);
    });
    scene.current?.updateWorldMatrix(true, true);
  });

  return <group ref={scene}>{children}</group>;
});
Reflect.displayName = "Reflect";
