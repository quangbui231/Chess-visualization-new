"use client";

import { useEffect, useMemo, useState } from "react";
import { useFilters } from "@/context/FilterContext";
import { ChartCard } from "@/components/ChartCard";
import { MetricCard } from "@/components/MetricCard";
import { ChartTooltip } from "@/components/ChartTooltip";
import "@/app/analytics.css";
import "@/app/tooltip.css";

const API = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
const SPEED_ORDER = ["UltraBullet", "Bullet", "Blitz", "Rapid", "Classical"];
const COLORS = ["#2878A8", "#2A9D8F", "#E69F00", "#7892A5", "#CE7B65"];
const OUTCOMES = [{ key: "white", label: "Trắng thắng", color: "#2878A8" }, { key: "black", label: "Đen thắng", color: "#E69F00" }, { key: "draw", label: "Hòa", color: "#2A9D8F" }];
type RQ1 = { speed: string; n: number; share: number };
type RQ2 = { rating_bin: number; n: number };
type RQ3 = { rating_gap_group: string; n: number; score: number; ci: number };
type RQ4 = { speed: string; n: number; score: number; ci: number };
type RQ5 = { speed: string; winner: string; n: number; share: number };
type RQ6 = { speed: string; n: number; forfeit_rate: number };
type RQ7 = { speed: string; total_moves: number };
type KPI = { n: number; white_win: number | null; black_win: number | null; draw: number | null; med_moves: number | null };
type PageData = { kpis?: KPI; rq1?: RQ1[]; rq2?: RQ2[]; rq3?: RQ3[]; rq4?: RQ4[]; rq5?: RQ5[]; rq6?: RQ6[]; rq7?: RQ7[] };

function useAnalytics(section: "overview" | "elo" | "time") {
  const { queryString } = useFilters();
  const [result, setResult] = useState<{ key: string; data: PageData; error: string | null } | null>(null);
  const requestKey = `${section}?${queryString}`;

  useEffect(() => {
    const controller = new AbortController();
    const endpoints = section === "overview" ? ["overview", "rq1", "rq2"] : section === "elo" ? ["rq3", "rq4", "rq5"] : ["rq6", "rq7"];
    const suffix = queryString ? `?${queryString}` : "";
    Promise.all(endpoints.map(async (endpoint) => {
      const extra = ["rq3", "rq4", "rq5"].includes(endpoint) ? `${suffix ? "&" : "?"}complete_only=true` : "";
      const response = await fetch(`${API}/api/${endpoint.startsWith("rq") ? `rq/${endpoint}` : endpoint}${suffix}${extra}`, { signal: controller.signal });
      if (!response.ok) throw new Error(`API ${endpoint}: ${response.status}`);
      return [endpoint, await response.json()] as const;
    }))
      .then((results) => {
        const next: PageData = {};
        for (const [endpoint, result] of results) {
          if (endpoint === "overview") next.kpis = result.kpis as KPI;
          else next[endpoint as keyof Omit<PageData, "kpis">] = result.data as never;
        }
        setResult({ key: requestKey, data: next, error: null });
      })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setResult({ key: requestKey, data: {}, error: reason instanceof Error ? reason.message : "Không thể tải dữ liệu từ API." });
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [section, queryString, requestKey]);
  const current = result?.key === requestKey ? result : null;
  return { data: current?.data ?? {}, loading: current === null, error: current?.error ?? null };
}

function EmptyChart({ loading, error, hasData }: { loading: boolean; error: string | null; hasData: boolean }) {
  if (loading) return <div className="chart-state"><span className="spinner" />Đang tải dữ liệu…</div>;
  if (error) return <div className="chart-state chart-error">Không tải được dữ liệu. {error}<small>Hãy kiểm tra backend API đang chạy ở localhost:8000.</small></div>;
  if (!hasData) return <div className="chart-state">Không có dữ liệu phù hợp với các bộ lọc đã chọn.</div>;
  return null;
}

function BarChart({ rows, label, format = (n: number) => n.toLocaleString("vi-VN"), suffix = "", horizontal = false }: { rows: { label: string; value: number; detail?: string; tooltip?: string }[]; label: string; format?: (n: number) => string; suffix?: string; horizontal?: boolean }) {
  const max = Math.max(...rows.map((r) => r.value), 0.0001);
  if (horizontal) return <div className="hbar-chart" role="img" aria-label={label}>{rows.map((row, i) => <div className="hbar-row" key={row.label} data-tooltip={row.tooltip ?? `${row.label}\n${format(row.value)}${suffix}`} tabIndex={0} aria-label={row.tooltip ?? `${row.label}: ${format(row.value)}${suffix}`}><span className="hbar-label">{row.label}</span><div className="hbar-track"><div className="hbar-fill" style={{ width: `${Math.max(1, row.value / max * 100)}%`, background: COLORS[i % COLORS.length] }} /></div><strong className="hbar-value">{format(row.value)}{suffix}</strong></div>)}</div>;
  const width = 680, height = 260, left = 52, right = 14, top = 15, bottom = 47, chartW = width - left - right, chartH = height - top - bottom;
  return <svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={label}>
    {[0, .25, .5, .75, 1].map((tick) => <g key={tick}><line x1={left} x2={width - right} y1={top + chartH * (1 - tick)} y2={top + chartH * (1 - tick)} stroke="#e8eef2" /><text x={left - 8} y={top + chartH * (1 - tick) + 4} textAnchor="end" className="axis-text">{format(max * tick)}{suffix}</text></g>)}
    {rows.map((row, i) => { const slot = chartW / rows.length; const barW = Math.min(55, slot * .54); const h = row.value / max * chartH; const showLabel = rows.length <= 14 || i % Math.ceil(rows.length / 8) === 0 || i === rows.length - 1; return <g key={row.label}><rect x={left + slot * i + (slot - barW) / 2} y={top + chartH - h} width={barW} height={Math.max(h, 1)} rx="5" fill={COLORS[i % COLORS.length]} data-tooltip={row.tooltip ?? `${row.label}\n${format(row.value)}${suffix}${row.detail ? `\n${row.detail}` : ""}`} tabIndex={0} role="img" aria-label={row.tooltip ?? `${row.label}: ${format(row.value)}${suffix}`} />{showLabel && <text x={left + slot * i + slot / 2} y={height - 18} textAnchor="middle" className="axis-text">{row.label}</text>}</g>; })}
  </svg>;
}

function ConfidenceChart({ rows, keyLabel, scoreLabel, title, fixedDomain = false, showMeanLabels = false }: { rows: { label: string; score: number; ci: number; n: number }[]; keyLabel: string; scoreLabel: string; title: string; fixedDomain?: boolean; showMeanLabels?: boolean }) {
  const rawMin = Math.min(.5, ...rows.map((row) => row.score - row.ci));
  const rawMax = Math.max(.5, ...rows.map((row) => row.score + row.ci));
  const min = fixedDomain ? 0 : Math.floor((rawMin - .05) / .05) * .05;
  const max = fixedDomain ? 1 : Math.ceil((rawMax + .05) / .05) * .05;
  const step = fixedDomain || max - min > .3 ? .1 : max - min > .15 ? .05 : .025;
  const ticks = Array.from({ length: Math.round((max - min) / step) + 1 }, (_, i) => Number((min + i * step).toFixed(3)));
  const width = 680, height = 270, left = 57, right = 17, top = 18, bottom = 54, chartH = height - top - bottom, chartW = width - left - right;
  const y = (v: number) => top + (max - v) / (max - min) * chartH;
  return <div className="confidence-wrap"><svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={title}>
    {ticks.map((tick) => <g key={tick}><line x1={left} x2={width-right} y1={y(tick)} y2={y(tick)} stroke={tick === .5 ? "#91a1ac" : "#e8eef2"} strokeDasharray={tick === .5 ? "5 5" : undefined} /><text x={left-8} y={y(tick)+4} textAnchor="end" className="axis-text">{tick.toFixed(2)}</text></g>)}
    {rows.map((row,i) => {
      const step=chartW/rows.length, x=left+step*(i+.5), low=row.score-row.ci, high=row.score+row.ci, color=COLORS[i%COLORS.length];
      const tooltip=`${keyLabel}: ${row.label}\n${scoreLabel}: ${row.score.toFixed(3)}\nKhoảng tin cậy 95%: ${low.toFixed(3)}–${high.toFixed(3)}\nCỡ mẫu: n=${row.n.toLocaleString("vi-VN")}`;
      return <g key={row.label} data-tooltip={tooltip} tabIndex={0} role="img" aria-label={tooltip}>
        <line x1={x} x2={x} y1={y(high)} y2={y(low)} stroke="white" strokeWidth="7" strokeLinecap="round"/>
        <line x1={x-9} x2={x+9} y1={y(high)} y2={y(high)} stroke="white" strokeWidth="7" strokeLinecap="round"/>
        <line x1={x-9} x2={x+9} y1={y(low)} y2={y(low)} stroke="white" strokeWidth="7" strokeLinecap="round"/>
        <line x1={x} x2={x} y1={y(high)} y2={y(low)} stroke={color} strokeWidth="3" strokeLinecap="round"/>
        <line x1={x-9} x2={x+9} y1={y(high)} y2={y(high)} stroke={color} strokeWidth="3" strokeLinecap="round"/>
        <line x1={x-9} x2={x+9} y1={y(low)} y2={y(low)} stroke={color} strokeWidth="3" strokeLinecap="round"/>
        <circle cx={x} cy={y(row.score)} r="6" fill={color} stroke="white" strokeWidth="2"/>
        {showMeanLabels&&<text x={x} y={y(row.score)-10} textAnchor="middle" fill="#17324D" fontSize="10" fontWeight="700" paintOrder="stroke" stroke="#fff" strokeWidth="3" strokeLinejoin="round">{row.score.toFixed(3)}</text>}
        <text x={x} y={height-25} textAnchor="middle" className="axis-text">{row.label}</text>
      </g>;
    })}
    <text x="14" y={height/2} transform={`rotate(-90 14 ${height/2})`} className="axis-title">{scoreLabel}</text><text x={width/2} y={height-4} textAnchor="middle" className="axis-title">{keyLabel}</text>
  </svg><div className="chart-legend"><span><i className="legend-dot"/>Điểm trung bình</span><span><i className="legend-line"/>Khoảng tin cậy 95%</span><span><i className="legend-dash"/>Mức cân bằng 0,50</span></div></div>;
}

function StackedChart({ rows }: { rows: RQ5[] }) {
  const speeds = SPEED_ORDER.filter((speed) => rows.some((row) => row.speed === speed));
  return <div className="stacked-chart">{speeds.map((speed) => <div className="stacked-row" key={speed}><span>{speed}</span><div className="stacked-track">{OUTCOMES.map((outcome) => { const row = rows.find((item) => item.speed === speed && item.winner === outcome.key); const total = rows.filter((item) => item.speed === speed).reduce((sum, item) => sum + item.n, 0); const tooltip = row ? `${speed}\n${outcome.label}: ${row.n.toLocaleString("vi-VN")} ván\nTỷ lệ: ${(row.share*100).toFixed(1)}%\nTổng số ván trong thể thức: n=${total.toLocaleString("vi-VN")}` : ""; return row ? <div key={outcome.key} style={{ width: `${row.share * 100}%`, background: outcome.color }} data-tooltip={tooltip} tabIndex={0} aria-label={tooltip} /> : null; })}</div></div>)}<div className="chart-legend">{OUTCOMES.map((item) => <span key={item.key}><i className="legend-dot" style={{ background: item.color }} />{item.label}</span>)}</div></div>;
}

function quantile(sorted: number[], p: number) { const index = (sorted.length - 1) * p, low = Math.floor(index), high = Math.ceil(index); return sorted[low] + (sorted[high] - sorted[low]) * (index - low); }
function BoxPlot({ rows }: { rows: RQ7[] }) {
  const stats = SPEED_ORDER.map((speed) => { const values = rows.filter((row) => row.speed === speed).map((row) => row.total_moves).sort((a,b)=>a-b); if (!values.length) return null; const q1=quantile(values,.25), med=quantile(values,.5), q3=quantile(values,.75), iqr=q3-q1, min=values[0], max=values.at(-1)!; return { speed, values, min, max, q1, med, q3, low: Math.max(min,q1-1.5*iqr), high: Math.min(max,q3+1.5*iqr) }; }).filter((item): item is NonNullable<typeof item> => item !== null);
  const width=680,height=285,left=55,right=18,top=15,bottom=51,max=Math.max(20,...stats.map(s=>s.high)),chartH=height-top-bottom,chartW=width-left-right,y=(v:number)=>top+chartH-(v/max)*chartH;
  return <><svg className="chart-svg" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Phân bố số nước đi theo thể thức thời gian">
    {[0,.25,.5,.75,1].map(t=><g key={t}><line x1={left} x2={width-right} y1={y(max*t)} y2={y(max*t)} stroke="#e8eef2"/><text x={left-8} y={y(max*t)+4} textAnchor="end" className="axis-text">{Math.round(max*t)}</text></g>)}
    {stats.map((s,i)=>{const slot=chartW/stats.length,x=left+slot*(i+.5),bw=Math.min(48,slot*.48),c=COLORS[i%COLORS.length];const tooltip=`Thể thức: ${s.speed}\nSố lượng mẫu: n=${s.values.length.toLocaleString("vi-VN")}\nMin (giá trị quan sát): ${s.min.toFixed(1)} nước\nQ1: ${s.q1.toFixed(1)} nước\nMedian: ${s.med.toFixed(1)} nước\nQ3: ${s.q3.toFixed(1)} nước\nMax (giá trị quan sát): ${s.max.toFixed(1)} nước\nHai đầu râu theo quy tắc 1,5×IQR: ${s.low.toFixed(1)}–${s.high.toFixed(1)} nước`;return <g key={s.speed} data-tooltip={tooltip} tabIndex={0} role="img" aria-label={tooltip}><line x1={x} x2={x} y1={y(s.high)} y2={y(s.low)} stroke={c} strokeWidth="2"/><line x1={x-8} x2={x+8} y1={y(s.high)} y2={y(s.high)} stroke={c} strokeWidth="2"/><line x1={x-8} x2={x+8} y1={y(s.low)} y2={y(s.low)} stroke={c} strokeWidth="2"/><rect x={x-bw/2} y={y(s.q3)} width={bw} height={Math.max(2,y(s.q1)-y(s.q3))} rx="3" fill={`${c}35`} stroke={c} strokeWidth="2"/><line x1={x-bw/2} x2={x+bw/2} y1={y(s.med)} y2={y(s.med)} stroke={c} strokeWidth="3"/><text x={x} y={height-23} textAnchor="middle" className="axis-text">{s.speed}</text></g>;})}
    <text x="14" y={height/2} transform={`rotate(-90 14 ${height/2})`} className="axis-title">Tổng số nước đi (nước)</text><text x={width/2} y={height-3} textAnchor="middle" className="axis-title">Thể thức thời gian</text>
  </svg><p className="chart-footnote">Hộp thể hiện 50% số ván ở giữa (Q1–Q3); đường giữa là trung vị. Râu dùng quy tắc 1,5×IQR. Mẫu tối đa 5.000 ván mỗi thể thức, đúng theo dashboard hiện tại.</p></>;
}

function Card({ title, subtitle, loading, error, hasData, children, className }: { title: string; subtitle?: string; loading: boolean; error: string | null; hasData: boolean; children: React.ReactNode; className?: string }) {
  return <ChartCard title={title} subtitle={subtitle} className={className}><EmptyChart loading={loading} error={error} hasData={hasData} />{!loading&&!error&&hasData&&<ChartTooltip>{children}</ChartTooltip>}</ChartCard>;
}

export function Analytics({ section }: { section: "overview" | "elo" | "time" }) {
  const { data, loading, error } = useAnalytics(section);
  const moveRows = useMemo(() => data.rq7 ?? [], [data.rq7]);
  if (section === "overview") return <>
    <div className="metrics-grid"><MetricCard label="Tổng số ván được lọc" value={data.kpis ? data.kpis.n.toLocaleString("vi-VN") : "—"} detail="ván đấu trong tập dữ liệu" accent="blue"/><MetricCard label="Trắng thắng" value={data.kpis?.white_win == null ? "—" : `${(data.kpis.white_win*100).toFixed(1)}%`} detail="tỷ lệ trên số ván đã lọc" accent="teal"/><MetricCard label="Đen thắng" value={data.kpis?.black_win == null ? "—" : `${(data.kpis.black_win*100).toFixed(1)}%`} detail="tỷ lệ trên số ván đã lọc" accent="blue"/><MetricCard label="Tỷ lệ hòa" value={data.kpis?.draw == null ? "—" : `${(data.kpis.draw*100).toFixed(1)}%`} detail="tỷ lệ trên số ván đã lọc" accent="orange"/><MetricCard label="Trung vị độ dài ván" value={data.kpis?.med_moves == null ? "—" : `${data.kpis.med_moves.toLocaleString("vi-VN")}`} detail="nước đi mỗi ván" accent="blue"/></div>
    <div className="charts-grid"><Card title="RQ1 · Thể thức thời gian nào phổ biến nhất?" subtitle="Số ván theo thể thức; thanh dài hơn nghĩa là xuất hiện nhiều hơn." loading={loading} error={error} hasData={!!data.rq1?.length}><BarChart rows={(data.rq1??[]).map(r=>{const total=(data.rq1??[]).reduce((sum,item)=>sum+item.n,0);return {label:r.speed,value:r.n,tooltip:`Thể thức: ${r.speed}\nSố ván trong nhóm: ${r.n.toLocaleString("vi-VN")}\nTỷ trọng: ${(r.share*100).toFixed(1)}%\nTổng số ván: n=${total.toLocaleString("vi-VN")}`};})} label="Số ván theo thể thức thời gian" horizontal/></Card><Card title="RQ2 · Mức Elo trung bình phân bố ra sao?" subtitle="Mỗi ván được xếp theo Elo trung bình của hai người chơi, chia bin 50 Elo." loading={loading} error={error} hasData={!!data.rq2?.length}><BarChart rows={(data.rq2??[]).map(r=>({label:`${r.rating_bin}–${r.rating_bin+49}`,value:r.n,tooltip:`Nhóm Elo trung bình mỗi ván: ${r.rating_bin}–${r.rating_bin+49}\nSố ván: ${r.n.toLocaleString("vi-VN")}\nTỷ trọng trong dữ liệu đã lọc: ${(r.n/(data.rq2??[]).reduce((sum,item)=>sum+item.n,0)*100).toFixed(1)}%\nCỡ mẫu: n=${r.n.toLocaleString("vi-VN")}`}))} label="Số ván theo nhóm Elo trung bình"/></Card></div>
  </>;
  if (section === "elo") return <>
    <div className="charts-grid"><Card className="chart-wide" title="RQ3 · Người Elo cao hơn có đạt điểm tốt hơn?" subtitle="Điểm của người có Elo cao hơn (thắng 1, hòa 0,5, thua 0), theo chênh lệch rating." loading={loading} error={error} hasData={!!data.rq3?.length}><ConfidenceChart rows={(data.rq3??[]).map(r=>({label:r.rating_gap_group,score:r.score,ci:r.ci,n:r.n}))} keyLabel="Nhóm chênh lệch Elo" scoreLabel="Điểm của người Elo cao hơn" title="Điểm trung bình và khoảng tin cậy 95% theo chênh lệch Elo" fixedDomain/></Card><Card title="RQ4 · Trắng có lợi thế khi Elo gần bằng nhau?" subtitle="Chỉ xét ván có chênh lệch Elo dưới 100; 0,50 là cân bằng." loading={loading} error={error} hasData={!!data.rq4?.length}><ConfidenceChart rows={(data.rq4??[]).map(r=>({label:r.speed,score:r.score,ci:r.ci,n:r.n}))} keyLabel="Thể thức thời gian" scoreLabel="Điểm của quân Trắng" title="Điểm trung bình quân Trắng theo thể thức" showMeanLabels/></Card><Card title="RQ5 · Kết quả ván khác nhau thế nào giữa các thể thức?" subtitle="Tỷ trọng thắng Trắng, thắng Đen và hòa trong từng thể thức." loading={loading} error={error} hasData={!!data.rq5?.length}><StackedChart rows={data.rq5??[]}/></Card></div>
    <p className="analysis-note">RQ3–RQ5 mặc định chỉ tính ván hoàn tất, theo đúng tùy chọn mặc định của dashboard Streamlit.</p>
  </>;
  return <div className="charts-grid"><Card title="RQ6 · Tỷ lệ ván kết thúc do hết giờ" subtitle="Tỷ lệ số ván bị xử thua do hết giờ trên tổng số ván theo từng thể thức." loading={loading} error={error} hasData={!!data.rq6?.length}><BarChart rows={(data.rq6??[]).map(r=>({label:r.speed,value:r.forfeit_rate*100,tooltip:`Thể thức: ${r.speed}\nTỷ lệ hết giờ: ${(r.forfeit_rate*100).toFixed(1)}%\nSố ván hết giờ: ${Math.round(r.forfeit_rate*r.n).toLocaleString("vi-VN")} ván\nTổng số ván tính tỷ lệ: n=${r.n.toLocaleString("vi-VN")}`}))} label="Tỷ lệ ván hết giờ theo thể thức" format={(n)=>n.toFixed(1)} suffix="%"/></Card><Card title="RQ7 · Độ dài ván thay đổi thế nào theo thể thức?" subtitle="Phân bố tổng số nước đi; trung vị và khoảng tứ phân vị giúp so sánh độ dài điển hình." loading={loading} error={error} hasData={moveRows.length>0}><BoxPlot rows={moveRows}/></Card></div>;
}
