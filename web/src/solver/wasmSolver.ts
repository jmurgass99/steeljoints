import type { SemanticBoltRow, SteelJointResult } from "../data-model.ts";
import { getConnectionGridMesh } from "../mesh/getMesh.ts";

// Binario WebAssembly compilado desde jointKernel.cpp
const WASM_B64 =
  "AGFzbQEAAAABDwJgBHx8fHwBfGACfHwBfAMDAgABBQMBAAEHKwISYm9sdFNoZWFyQ29tcG9uZW50AAAScGxhdGVCZW5kaW5nTW9tZW50AAEKIQINACAAIAGjIAIgA6KgCxEAIAAgAaJEAAAAAAAA4D+iCw==";

function decodeBase64(b64: string): Uint8Array {
  if (typeof Buffer !== "undefined") {
    return new Uint8Array(Buffer.from(b64, "base64"));
  }
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export interface JointWasmExports {
  boltShearComponent: (vDir: number, nBolts: number, mz: number, coordOverJ: number) => number;
  plateBendingMoment: (ft: number, mArm: number) => number;
}

let cachedExports: JointWasmExports | null = null;

export async function initJointWasm(): Promise<JointWasmExports> {
  if (cachedExports) return cachedExports;
  const { instance } = await WebAssembly.instantiate(decodeBase64(WASM_B64));
  cachedExports = instance.exports as unknown as JointWasmExports;
  return cachedExports;
}

export async function solveSteelJointWasm(
  shearVKn: number,
  momentMKnm: number,
  rows: SemanticBoltRow[],
  plateThicknessMm: number
): Promise<SteelJointResult> {
  const wasm = await initJointWasm();
  const { bolts, mapping } = getConnectionGridMesh(rows);
  const n = Math.max(bolts.length, 1);

  const cx = bolts.reduce((acc, b) => acc + b.xMm, 0) / n;
  const cy = bolts.reduce((acc, b) => acc + b.yMm, 0) / n;
  const jPolar = bolts.reduce((acc, b) => acc + Math.pow(b.xMm - cx, 2) + Math.pow(b.yMm - cy, 2), 0);
  const iY = bolts.reduce((acc, b) => acc + Math.pow(b.yMm - cy, 2), 0);

  let maxVKn = 0;
  let maxTKn = 0;

  for (const b of bolts) {
    const dy = b.yMm - cy;
    const coordOverJ = jPolar > 0 ? (b.xMm - cx) / jPolar : 0;
    b.vxKn = 0;
    b.vyKn = wasm.boltShearComponent(-shearVKn, n, 0, coordOverJ);
    b.vTotalKn = Math.sqrt(b.vxKn * b.vxKn + b.vyKn * b.vyKn);

    if (dy > 0 && iY > 0) {
      b.tTensionKn = Math.max(0, (momentMKnm * 1000 * dy) / iY);
    } else {
      b.tTensionKn = 0;
    }

    if (b.vTotalKn > maxVKn) maxVKn = b.vTotalKn;
    if (b.tTensionKn > maxTKn) maxTKn = b.tTensionKn;
  }

  const pryingArm = 38.0;
  const pryingForceKn = maxTKn * Math.max(0.05, 0.35 - (plateThicknessMm / 80));
  const plateMomentKnm = wasm.plateBendingMoment(maxTKn, pryingArm) / 1000;

  return { bolts, mapping, maxVKn, maxTKn, pryingForceKn, plateMomentKnm };
}
