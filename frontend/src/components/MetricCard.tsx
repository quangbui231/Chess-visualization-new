export function MetricCard({ label, value, detail, accent = "blue" }: { label: string; value: string; detail?: string; accent?: "blue" | "teal" | "orange" }) {
  return <article className={`metric-card metric-${accent}`}><span className="metric-label">{label}</span><strong className="metric-value">{value}</strong>{detail && <span className="metric-detail">{detail}</span>}</article>;
}
