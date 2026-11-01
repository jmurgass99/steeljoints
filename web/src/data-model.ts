export interface SemanticBoltRow {
  id: string;
  yCoordMm: number;
  numBolts: number;
  gageMm: number;
}

export interface ConnectionGridMapping {
  rowToBolts: Map<string, number[]>;
  boltToRow: Map<number, string>;
  plateToYieldLines: Map<string, number[]>;
}

export interface DiscretizedBoltNode {
  index: number;
  rowId: string;
  xMm: number;
  yMm: number;
  vxKn: number;
  vyKn: number;
  vTotalKn: number;
  tTensionKn: number;
}

export interface SteelJointResult {
  bolts: DiscretizedBoltNode[];
  mapping: ConnectionGridMapping;
  maxVKn: number;
  maxTKn: number;
  pryingForceKn: number;
  plateMomentKnm: number;
}
