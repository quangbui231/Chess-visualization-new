import { DashboardShell } from "@/components/DashboardShell";
import { FilterPanel } from "@/components/FilterPanel";
import { Analytics } from "@/components/Analytics";

const sections = {
  overview: { eyebrow: "TỔNG QUAN", title: "Bức tranh toàn cảnh", description: "Khám phá các mẫu hình trong 400.000 ván cờ trực tuyến từ Lichess.", tags: ["Tổng quan dữ liệu", "RQ1 · RQ2"] },
  elo: { eyebrow: "ELO & KẾT QUẢ", title: "Năng lực và kết quả", description: "Tìm hiểu mối liên hệ giữa mức Elo, chênh lệch trình độ và kết quả ván đấu.", tags: ["So sánh người chơi", "RQ3 · RQ4 · RQ5"] },
  time: { eyebrow: "THỜI GIAN & DIỄN BIẾN", title: "Nhịp độ của ván cờ", description: "So sánh cách thể thức thời gian ảnh hưởng đến kết thúc và độ dài ván đấu.", tags: ["Thời lượng ván", "RQ6 · RQ7"] },
};

export function DashboardPage({ section }: { section: keyof typeof sections }) {
  const page = sections[section];
  return <DashboardShell><div className="page-heading"><div><div className="eyebrow"><span />{page.eyebrow}</div><h1>{page.title}</h1><p>{page.description}</p></div><div className="page-tags">{page.tags.map((tag) => <span key={tag}>{tag}</span>)}</div></div>
    <FilterPanel />
    <Analytics section={section} />
  </DashboardShell>;
}
