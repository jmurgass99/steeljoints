import * as THREE from "three";
import type { SteelJointResult } from "../data-model.ts";

export function createSteelJointViewer3D(container: HTMLElement): {
  update: (res: SteelJointResult, plateThicknessMm: number) => void;
} {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x080d14);

  const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1500);
  camera.position.set(240, 180, 360);
  camera.lookAt(0, 40, 0);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  container.appendChild(renderer.domElement);

  const ambient = new THREE.AmbientLight(0xffffff, 0.72);
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(200, 300, 250);
  scene.add(ambient, dir);

  const group = new THREE.Group();
  scene.add(group);

  const resize = () => {
    const w = container.clientWidth || 640;
    const h = container.clientHeight || 480;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  };
  window.addEventListener("resize", resize);
  setTimeout(resize, 0);

  const animate = () => {
    requestAnimationFrame(animate);
    group.rotation.y += 0.003;
    renderer.render(scene, camera);
  };
  animate();

  return {
    update(res: SteelJointResult, plateThicknessMm: number) {
      while (group.children.length > 0) group.remove(group.children[0]);

      // Chapa de testero (End-plate)
      const plateGeo = new THREE.BoxGeometry(220, 420, plateThicknessMm);
      const plateMat = new THREE.MeshStandardMaterial({
        color: 0x64748b,
        metalness: 0.6,
        roughness: 0.35,
      });
      const plate = new THREE.Mesh(plateGeo, plateMat);
      plate.position.set(0, 40, 0);
      group.add(plate);

      // Líneas de fluencia en chapa (Yield lines)
      const lineMat = new THREE.LineBasicMaterial({ color: 0xef4444 });
      const points = [
        new THREE.Vector3(-100, 140, plateThicknessMm / 2 + 0.5),
        new THREE.Vector3(100, 140, plateThicknessMm / 2 + 0.5),
      ];
      const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
      const yieldLine = new THREE.Line(lineGeo, lineMat);
      group.add(yieldLine);

      // Pernos y flechas de vector fuerza cortante + tracción
      const vMax = Math.max(res.maxVKn, 1);
      const tMax = Math.max(res.maxTKn, 1);

      res.bolts.forEach((b) => {
        const boltGeo = new THREE.CylinderGeometry(10, 10, plateThicknessMm + 16, 16);
        const boltMat = new THREE.MeshStandardMaterial({ color: 0xe2e8f0 });
        const bolt = new THREE.Mesh(boltGeo, boltMat);
        bolt.rotation.x = Math.PI / 2;
        bolt.position.set(b.xMm, b.yMm, 0);
        group.add(bolt);

        // Vector de tracción (hacia +Z)
        if (b.tTensionKn > 0.5) {
          const arrowLen = (b.tTensionKn / tMax) * 45;
          const arrowT = new THREE.ArrowHelper(
            new THREE.Vector3(0, 0, 1),
            new THREE.Vector3(b.xMm, b.yMm, plateThicknessMm / 2 + 8),
            arrowLen,
            0xf59e0b,
            8,
            5
          );
          group.add(arrowT);
        }

        // Vector de corte (hacia -Y)
        const arrowVLen = (b.vTotalKn / vMax) * 35;
        const arrowV = new THREE.ArrowHelper(
          new THREE.Vector3(0, -1, 0),
          new THREE.Vector3(b.xMm, b.yMm, plateThicknessMm / 2 + 8),
          arrowVLen,
          0x38bdf8,
          6,
          4
        );
        group.add(arrowV);
      });
    },
  };
}
