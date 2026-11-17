import type { ReactNode } from "react";

export function ChartCard({ title, subtitle, children, className = "" }: { title: string; subtitle?: string; children: ReactNode; className?: string }) {
  return <section className={`chart-card ${className}`}><header className="chart-card-header"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div></header><div className="chart-card-body">{children}</div></section>;
}
