import type { Axis, HistoryPlot, HistoryPoint } from "./types";

const TOP = 25;
const BOTTOM = 245;
const MAX_QUARTER_GAP_DAYS = 100;

function numeric(point: HistoryPoint): number | null {
  if (point.y === null) return null;
  const percent = point.valueLabel.endsWith("%");
  const value = Number(point.valueLabel.replace(/[%×,]/g, ""));
  if (!Number.isFinite(value)) return null;
  return percent ? value / 100 : value;
}

function tickLabel(value: number, unit: string) {
  const displayed = unit === "fraction" ? value * 100 : value;
  const suffix = unit === "fraction" ? "%" : "×";
  return `${displayed.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${suffix}`;
}

function pathFor(points: HistoryPoint[]) {
  const paths: string[] = [];
  let segment: string[] = [];
  let previous: Date | null = null;
  for (const point of points) {
    const current = new Date(`${point.asOf}T00:00:00Z`);
    const gap = previous !== null && (current.getTime() - previous.getTime()) / 86_400_000 > MAX_QUARTER_GAP_DAYS;
    if (point.y === null || gap) {
      if (segment.length) paths.push(segment.join(" "));
      segment = [];
    }
    if (point.y !== null) segment.push(`${segment.length ? "L" : "M"} ${point.x} ${point.y}`);
    previous = current;
  }
  if (segment.length) paths.push(segment.join(" "));
  return paths;
}

/** Display geometry only. Exact values, status and eligibility remain exporter supplied. */
export function scaleHistory(data: HistoryPlot, selected: string[]): Pick<HistoryPlot, "series" | "yAxis"> {
  const series = data.series.filter((item) => selected.includes(item.sectorId));
  const values = series.flatMap((item) => item.points.map(numeric)).filter((value): value is number => value !== null);
  if (!values.length) return { series, yAxis: data.yAxis };
  const unit = series.some((item) =>
    item.points.some((point) => point.y !== null && point.valueLabel.endsWith("%")),
  )
    ? "fraction"
    : "multiple";

  const observedLow = Math.min(...values);
  const observedHigh = Math.max(...values);
  const spread = observedHigh - observedLow;
  const padding = spread === 0 ? Math.max(Math.abs(observedHigh) * 0.05, 1) : spread * 0.08;
  const low = observedLow - padding;
  const high = observedHigh + padding;
  const y = (value: number) => Math.round((BOTTOM - ((value - low) / (high - low)) * (BOTTOM - TOP)) * 10_000) / 10_000;

  const scaled = series.map((item) => {
    const points = item.points.map((point) => {
      const value = numeric(point);
      return { ...point, y: value === null ? null : y(value) };
    });
    return { ...item, points, paths: pathFor(points) };
  });
  const ticks = Array.from({ length: 5 }, (_, index) => {
    const value = low + ((high - low) * index) / 4;
    return { position: y(value), label: tickLabel(value, unit) };
  });
  const yAxis: Axis = { ticks, zero: y(0) };
  return { series: scaled, yAxis };
}
