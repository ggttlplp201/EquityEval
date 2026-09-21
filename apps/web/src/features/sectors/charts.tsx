"use client";

import { useId } from "react";
import type { Axis, Distribution, HistoryPlot, ScatterPlot, Sector } from "./types";

const EMPTY_SECTOR: Sector = { id: "unknown", label: "Unclassified", color: "#748287" };
function lookup(sectors: Sector[], id: string) { return sectors.find((sector) => sector.id === id) ?? EMPTY_SECTOR; }
export function historyLinePattern(index: number) {
  return ["none", "8 4", "2 4", "8 3 2 3"][index] ?? "none";
}
function activate(event: React.KeyboardEvent, action: () => void) {
  if (event.key === "Enter" || event.key === " ") { event.preventDefault(); action(); }
}
export function PlotAxes({ xAxis, yAxis }: { xAxis: Axis; yAxis: Axis }) {
  return <g className="plot-axes" aria-hidden="true">
    {yAxis.ticks.map((tick) => <g key={`${tick.label}-${tick.position}`}><line x1="60" x2="730" y1={tick.position} y2={tick.position} /><text x="47" y={tick.position} textAnchor="end" dominantBaseline="middle">{tick.label}</text></g>)}
    {xAxis.ticks.map((tick, index) => <text key={`${tick.label}-${tick.position}`} x={tick.position} y="270" textAnchor={index === xAxis.ticks.length - 1 ? "end" : index === 0 ? "start" : "middle"}>{tick.label}</text>)}
  </g>;
}
export function HistoryChart({ data, selected, slots, sectors, onDetail, describeDetail }: { data: HistoryPlot; selected: string[]; slots: Record<string, number>; sectors: Sector[]; onDetail: (id: string) => void; describeDetail: (id: string) => string }) {
  const id = useId();
  const series = data.series.filter((item) => selected.includes(item.sectorId));
  return <>
    <div className="plot-scroll" tabIndex={0} role="region" aria-label="Chart; scroll horizontally on smaller screens"><svg className="analytical-plot" viewBox="-16 0 776 285" role="group" aria-labelledby={`${id}-title ${id}-desc`}>
      <title id={`${id}-title`}>Quarter-end history of the selected metric</title>
      <desc id={`${id}-desc`}>Gaps indicate unavailable or limited-coverage observations. Use the history data table for all dates and values.</desc>
      <PlotAxes xAxis={data.xAxis} yAxis={data.yAxis} />
      {series.map((item) => <g key={item.sectorId} style={{ color: "var(--accent)" }}>
        {item.paths.map((path, index) => <path key={index} d={path} fill="none" stroke="currentColor" strokeWidth="2.5" strokeDasharray={historyLinePattern(slots[item.sectorId])} />)}
        {item.points.filter((point) => point.y !== null).map((point) => <circle key={point.asOf} cx={point.x} cy={point.y!} r="4" fill="var(--surface)" stroke="currentColor" strokeWidth="2" tabIndex={0} role="button" aria-label={`${lookup(sectors, item.sectorId).label}, ${point.asOf}: ${point.valueLabel}. Open source details.`} onClick={() => onDetail(point.detailId)} onKeyDown={(event) => activate(event, () => onDetail(point.detailId))}><title>{`${lookup(sectors, item.sectorId).label} · ${point.asOf} · ${point.valueLabel} · ${point.status}\n${describeDetail(point.detailId)}`}</title></circle>)}
      </g>)}
    </svg></div>
    <p className="chart-note">{data.note}</p>
    <details className="data-table"><summary>History data & sources</summary><div className="table-scroll"><table><caption>Quarter-end values, including gaps</caption><thead><tr><th>Sector</th><th>Date</th><th>Value</th><th>Status</th></tr></thead><tbody>{series.flatMap((item) => item.points.map((point) => <tr key={`${item.sectorId}-${point.asOf}`}><td>{lookup(sectors, item.sectorId).label}</td><td>{point.asOf}</td><td><button className="text-button" onClick={() => onDetail(point.detailId)}>{point.valueLabel}</button></td><td>{point.status}</td></tr>))}</tbody></table></div></details>
  </>;
}
export function DistributionChart({ data, activeBin, pinnedCompany, onBin, onDetail, describeDetail }: { data: Distribution; activeBin: string | null; pinnedCompany: string | null; onBin: (id: string | null) => void; onDetail: (id: string) => void; describeDetail: (id: string) => string }) {
  const id = useId();
  const pinned = data.companies.find((company) => company.id === pinnedCompany);
  return <>
    {data.emptyReason ? <div className="empty-chart">{data.emptyReason}</div> : <div className="plot-scroll" tabIndex={0} role="region" aria-label="Chart; scroll horizontally on smaller screens"><svg className="analytical-plot" viewBox="-16 0 776 285" role="group" aria-labelledby={`${id}-title ${id}-desc`}>
      <title id={`${id}-title`}>Distribution of eligible company values</title><desc id={`${id}-desc`}>All eligible observations are included. Choose a histogram bin to filter the company table.</desc>
      <PlotAxes xAxis={data.xAxis} yAxis={data.yAxis} />
      {data.bins.map((bin) => <rect key={bin.id} x={bin.x} y={bin.y} width={bin.width} height={bin.height} rx="2" className={activeBin === bin.id ? "histogram-bin selected" : "histogram-bin"} tabIndex={0} role="button" aria-label={`${bin.label}: ${bin.countLabel} companies. Filter constituent table.`} aria-pressed={activeBin === bin.id} onClick={() => onBin(activeBin === bin.id ? null : bin.id)} onKeyDown={(event) => activate(event, () => onBin(activeBin === bin.id ? null : bin.id))}><title>{`${bin.label} · ${bin.countLabel} companies\n${describeDetail(data.detailId)}`}</title></rect>)}
      {data.markers.map((marker) => <g key={marker.label}><line x1={marker.x} x2={marker.x} y1="20" y2="245" stroke="var(--ink)" strokeDasharray={marker.label === "Median" ? undefined : "3 4"} strokeWidth={marker.label === "Median" ? "2" : "1"} /><title>{`${marker.label}: ${marker.valueLabel}`}</title></g>)}
      {pinned && pinned.position !== null ? <g transform={`translate(${pinned.position}, 15)`}><line x1="0" x2="0" y1="0" y2="230" className="pin-line" /><circle r="6" className="pin-dot" /><text x="9" y="-2" className="pin-label">{pinned.ticker}</text></g> : null}
    </svg></div>}
    <div className="percentile-key">{data.markers.map((marker) => <span key={marker.label}>{marker.label}<button className="text-button" onClick={() => onDetail(data.detailId)}><strong>{marker.valueLabel}</strong></button></span>)}</div>
    {pinned && pinned.position === null ? <p className="chart-note">{pinned.ticker} cannot be plotted: {pinned.status}. Its source snapshot remains available.</p> : null}
    <div className="exclusion-strip">{data.excluded.map((item) => <span key={item.label}><strong>{item.count}</strong> {item.label}</span>)}</div>
    <p className="chart-note">Full observed range. No outliers are trimmed or capped. Bin selection filters the table below.</p>
    <details className="data-table"><summary>Distribution data</summary><div className="table-scroll"><table><caption>Eligible company distribution</caption><thead><tr><th>Interval</th><th>Companies</th><th>Action</th></tr></thead><tbody>{data.bins.map((bin) => <tr key={bin.id}><td>{bin.label}</td><td>{bin.countLabel}</td><td><button className="text-button" onClick={() => onBin(activeBin === bin.id ? null : bin.id)}>{activeBin === bin.id ? "Clear filter" : "Show companies"}</button></td></tr>)}</tbody></table></div></details>
    {pinned ? <button className="text-button pin-source" onClick={() => onDetail(pinned.detailId)}>Open {pinned.ticker}’s frozen fundamentals →</button> : null}
  </>;
}
export function ScatterChart({ data, sectors, sized, selected, onSelect, onDetail, describeDetail }: { data: ScatterPlot; sectors: Sector[]; sized: boolean; selected: string; onSelect: (id: string) => void; onDetail: (id: string) => void; describeDetail: (id: string) => string }) {
  const id = useId();
  return <>
    <div className="plot-scroll" tabIndex={0} role="region" aria-label="Growth versus valuation chart; scroll horizontally on smaller screens"><svg className="analytical-plot scatter-plot" viewBox="-16 0 776 285" role="group" aria-labelledby={`${id}-title ${id}-desc`}>
      <title id={`${id}-title`}>Growth versus valuation</title><desc id={`${id}-desc`}>Trailing P/E on the horizontal axis and TTM revenue year-over-year growth on the vertical axis. Only sectors passing both coverage gates are placed.</desc>
      <PlotAxes xAxis={data.xAxis} yAxis={data.yAxis} />
      {data.points.map((point) => <g key={point.sectorId} transform={`translate(${point.x}, ${point.y})`}><circle r={sized ? point.radius : 6} fill="var(--accent)" stroke={selected === point.sectorId ? "var(--ink)" : "var(--surface)"} strokeWidth="2" tabIndex={0} role="button" aria-label={`${lookup(sectors, point.sectorId).label}: P/E ${point.xLabel}, growth ${point.yLabel}. Select sector.`} onClick={() => onSelect(point.sectorId)} onKeyDown={(event) => activate(event, () => onSelect(point.sectorId))}><title>{`${lookup(sectors, point.sectorId).label} · P/E ${point.xLabel} · Growth ${point.yLabel}\n${describeDetail(point.detailId)}\n${describeDetail(point.growthDetailId)}`}</title></circle><text x={point.x > 620 ? -11 : 11} y="-9" textAnchor={point.x > 620 ? "end" : "start"} className="scatter-label">{lookup(sectors, point.sectorId).label}</text></g>)}
    </svg></div>
    <div className="scatter-axis-labels"><span>Y · {data.yLabel}</span><span>X · {data.xLabel}</span></div>
    {data.unavailable.length ? <details className="unavailable-list" open><summary>Not placed — missing, N/M or limited coverage</summary><ul>{data.unavailable.map((item) => <li key={item.sectorId}><button className="text-button" onClick={() => onSelect(item.sectorId)}>{lookup(sectors, item.sectorId).label}</button><span>{item.reason}</span></li>)}</ul></details> : null}
    <details className="data-table"><summary>Scatter data & sources</summary><div className="table-scroll"><table><caption>Growth and valuation use the selected calculation method</caption><thead><tr><th>Sector</th><th>Trailing P/E</th><th>Revenue YoY</th><th>Sources</th></tr></thead><tbody>{data.points.map((point) => <tr key={point.sectorId}><td>{lookup(sectors, point.sectorId).label}</td><td>{point.xLabel}</td><td>{point.yLabel}</td><td><button className="text-button" onClick={() => onDetail(point.detailId)}>P/E</button> · <button className="text-button" onClick={() => onDetail(point.growthDetailId)}>Growth</button></td></tr>)}</tbody></table></div></details>
  </>;
}
