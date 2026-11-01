import assert from "node:assert/strict";
import { solveSteelJointWasm } from "../solver/wasmSolver.ts";

const rows = [
  { id: "ROW-1", yCoordMm: 180, numBolts: 2, gageMm: 110 },
  { id: "ROW-2", yCoordMm: 100, numBolts: 2, gageMm: 110 },
  { id: "ROW-3", yCoordMm: -40, numBolts: 2, gageMm: 110 },
  { id: "ROW-4", yCoordMm: -120, numBolts: 2, gageMm: 110 },
];

const res4 = await solveSteelJointWasm(130, 65, rows.slice(0, 2), 22);
const res8 = await solveSteelJointWasm(130, 65, rows, 22);

assert.equal(res4.bolts.length, 4);
assert.equal(res8.bolts.length, 8);
assert.equal(res8.mapping.rowToBolts.get("ROW-1")?.length, 2);
assert.ok(res8.maxVKn < res4.maxVKn);
assert.ok(res8.maxTKn > 10.0);
console.log(
  `SteelJoints WASM test OK: V_max=${res8.maxVKn.toFixed(1)} kN, T_max=${res8.maxTKn.toFixed(1)} kN, Q_prying=${res8.pryingForceKn.toFixed(1)} kN`
);
