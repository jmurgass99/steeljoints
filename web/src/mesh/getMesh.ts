import type { ConnectionGridMapping, DiscretizedBoltNode, SemanticBoltRow } from "../data-model.ts";

export function getConnectionGridMesh(
  rows: SemanticBoltRow[]
): { bolts: DiscretizedBoltNode[]; mapping: ConnectionGridMapping } {
  const rowToBolts = new Map<string, number[]>();
  const boltToRow = new Map<number, string>();
  const plateToYieldLines = new Map<string, number[]>();
  const bolts: DiscretizedBoltNode[] = [];

  for (const r of rows) {
    const indices: number[] = [];
    const halfG = r.gageMm / 2;
    const xCoords = r.numBolts === 2 ? [-halfG, halfG] : [0];
    for (const x of xCoords) {
      const idx = bolts.length;
      bolts.push({
        index: idx,
        rowId: r.id,
        xMm: x,
        yMm: r.yCoordMm,
        vxKn: 0,
        vyKn: 0,
        vTotalKn: 0,
        tTensionKn: 0,
      });
      indices.push(idx);
      boltToRow.set(idx, r.id);
    }
    rowToBolts.set(r.id, indices);
  }

  plateToYieldLines.set("YIELD_FLANGE", rowToBolts.get(rows[0]?.id ?? "") ?? []);
  plateToYieldLines.set("YIELD_WEB", rowToBolts.get(rows[1]?.id ?? "") ?? []);

  return {
    bolts,
    mapping: { rowToBolts, boltToRow, plateToYieldLines },
  };
}
