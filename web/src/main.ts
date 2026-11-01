import van from "vanjs-core";
import type { SemanticBoltRow } from "./data-model.ts";
import { solveSteelJointWasm } from "./solver/wasmSolver.ts";
import { fetchSteeljointsHealthApi } from "./solver/apiClient.ts";
import { createSteelJointViewer3D } from "./viewer/getViewer3D.ts";
import { renderBoltForcesPolarChart, renderTensionPryingChart } from "./ui/getJointCharts.ts";

const { div, h2, h3, label, input, span, strong, canvas, button } = van.tags;

const shearV = van.state(130);
const momentM = van.state(65);
const plateThickness = van.state(22);
const rowCount = van.state(4);

const maxVText = van.state("0.0 kN");
const maxTText = van.state("0.0 kN");
const pryingText = van.state("0.0 kN");
const boltsText = van.state("8");
const apiStatus = van.state("Modo WASM local");

const viewerWrap = div({ class: "viewer-wrap" });
const vCanvas = canvas({ class: "chart" });
const tCanvas = canvas({ class: "chart" });
const viewer = createSteelJointViewer3D(viewerWrap);

async function recompute() {
  const allRows: SemanticBoltRow[] = [
    { id: "ROW-1-TENSION", yCoordMm: 180, numBolts: 2, gageMm: 110 },
    { id: "ROW-2-TENSION", yCoordMm: 100, numBolts: 2, gageMm: 110 },
    { id: "ROW-3-SHEAR", yCoordMm: -40, numBolts: 2, gageMm: 110 },
    { id: "ROW-4-SHEAR", yCoordMm: -120, numBolts: 2, gageMm: 110 },
  ];
  const activeRows = allRows.slice(0, rowCount.val);
  const res = await solveSteelJointWasm(
    shearV.val,
    momentM.val,
    activeRows,
    plateThickness.val
  );
  maxVText.val = `${res.maxVKn.toFixed(1)} kN`;
  maxTText.val = `${res.maxTKn.toFixed(1)} kN`;
  pryingText.val = `${res.pryingForceKn.toFixed(1)} kN`;
  boltsText.val = `${res.bolts.length}`;
  viewer.update(res, plateThickness.val);
  renderBoltForcesPolarChart(vCanvas, res);
  renderTensionPryingChart(tCanvas, res);
}

van.derive(() => {
  void recompute();
});

const app = div(
  { class: "layout" },
  div(
    { class: "panel" },
    h2("SteelJoints 3D"),
    div(
      { class: "control-row" },
      label(() => `Cortante V_u = ${shearV.val} kN`),
      input({
        type: "range",
        min: "20",
        max: "300",
        step: "10",
        value: shearV,
        oninput: (e: Event) => (shearV.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Momento flector M_u = ${momentM.val} kN·m`),
      input({
        type: "range",
        min: "10",
        max: "150",
        step: "5",
        value: momentM,
        oninput: (e: Event) => (momentM.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Espesor de chapa t_p = ${plateThickness.val} mm`),
      input({
        type: "range",
        min: "12",
        max: "40",
        step: "2",
        value: plateThickness,
        oninput: (e: Event) => (plateThickness.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "control-row" },
      label(() => `Filas de pernos (ConnectionGridMapping) = ${rowCount.val}`),
      input({
        type: "range",
        min: "2",
        max: "4",
        step: "1",
        value: rowCount,
        oninput: (e: Event) => (rowCount.val = Number((e.target as HTMLInputElement).value)),
      })
    ),
    div(
      { class: "kpi-grid" },
      div({ class: "kpi" }, span("Cortante perno V_i"), strong(maxVText)),
      div({ class: "kpi" }, span("Tracción perno T_i"), strong(maxTText)),
      div({ class: "kpi" }, span("Palanca Q (Prying)"), strong(pryingText)),
      div({ class: "kpi" }, span("Pernos activos"), strong(boltsText))
    ),
    button(
      {
        onclick: async () => {
          const ok = await fetchSteeljointsHealthApi("http://localhost:8000");
          apiStatus.val = ok ? "FastAPI sincronizado OK" : "FastAPI offline (usando WASM local)";
        },
      },
      "Sincronizar con FastAPI"
    ),
    span({ style: "font-size:0.75rem;color:#94a3b8" }, apiStatus)
  ),
  viewerWrap,
  div(
    { class: "panel" },
    h3("Distribución de Cortante por Perno"),
    vCanvas,
    h3("Tracción y Efecto Palanca (AISC DG4)"),
    tCanvas
  )
);

document.getElementById("app")?.appendChild(app);
