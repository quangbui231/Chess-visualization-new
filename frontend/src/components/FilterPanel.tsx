"use client";

import { useFilters } from "@/context/FilterContext";

const gameTypeLabels = { all: "Tất cả ván đấu", tournament: "Trong giải đấu", non_tournament: "Ngoài giải đấu" };

function MultiSelect({ label, values, selected, onChange }: { label: string; values: string[]; selected: string[]; onChange: (value: string[]) => void }) {
  return <details className="filter-multi"><summary><span>{label}</span><b>{selected.length ? `${selected.length} đã chọn` : "Tất cả"}</b><span className="chevron">⌄</span></summary>
    <div className="filter-options">{values.map((value) => <label key={value}><input type="checkbox" checked={selected.includes(value)} onChange={(event) => onChange(event.target.checked ? [...selected, value] : selected.filter((item) => item !== value))} />{value}</label>)}</div>
  </details>;
}

export function FilterPanel() {
  const { speed, rating_band, game_type, options, status, error, setFilter } = useFilters();
  return <section className="filter-panel" aria-label="Bộ lọc dữ liệu">
    <div className="filter-heading"><span className="filter-symbol">☷</span><div><strong>Bộ lọc dữ liệu</strong><small>Áp dụng đồng bộ cho các phân tích</small></div></div>
    {status === "error" && <p className="filter-error" role="status">{error ?? "Không kết nối được API."} <span>Kiểm tra backend tại localhost:8000</span></p>}
    <div className="filter-controls">
      <MultiSelect label="Thể thức thời gian" values={options?.speed ?? []} selected={speed} onChange={(value) => setFilter("speed", value)} />
      <MultiSelect label="Nhóm Elo trung bình" values={options?.rating_band ?? []} selected={rating_band} onChange={(value) => setFilter("rating_band", value)} />
      <label className="filter-select"><span>Loại ván đấu</span><select value={game_type} onChange={(event) => setFilter("game_type", event.target.value as typeof game_type)} disabled={!options}>{options?.game_type.map((item) => <option key={item.value} value={item.value}>{gameTypeLabels[item.value]}</option>)}</select></label>
    </div>
    <span className="filter-live"><i /> Bộ lọc đang hoạt động</span>
  </section>;
}
