"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, type ReactNode } from "react";
import { FilterProvider, useFilters } from "@/context/FilterContext";

const navigation = [
  { href: "/", label: "Tổng quan", icon: "◫", group: "PHÂN TÍCH" },
  { href: "/elo", label: "Elo & kết quả", icon: "↗" },
  { href: "/thoi-gian", label: "Thời gian & ván đấu", icon: "◷" },
];

function Sidebar() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const filterQuery = searchParams.toString();
  return <aside className="sidebar">
    <Link className="brand" href="/"><span className="brand-mark">♞</span><span>CHESS<span className="brand-light">/DATA</span><small>LICHESS ANALYTICS</small></span></Link>
    <div className="nav-caption">{navigation[0].group}</div>
    <nav aria-label="Điều hướng chính">
      {navigation.map((item, index) => <div key={item.href}>
        {index === 1 && <div className="nav-caption nav-caption-spaced">KẾT QUẢ & DIỄN BIẾN</div>}
        <Link className={`nav-link ${pathname === item.href ? "active" : ""}`} href={`${item.href}${filterQuery ? `?${filterQuery}` : ""}`} aria-current={pathname === item.href ? "page" : undefined}>
          <span className="nav-icon">{item.icon}</span>{item.label}{pathname === item.href && <span className="nav-indicator" />}
        </Link>
      </div>)}
    </nav>
    <div className="sidebar-foot"><span className="status-dot" /> Dữ liệu nghiên cứu<br /><small>400.000 ván Lichess</small></div>
  </aside>;
}

function Header() {
  const { status } = useFilters();
  return <header className="topbar"><div className="breadcrumb">Nghiên cứu dữ liệu <span>/</span> <strong>Dashboard</strong></div><div className="topbar-right"><span className={`api-status ${status === "ready" ? "online" : ""}`}><i />{status === "ready" ? "API đã kết nối" : status === "loading" ? "Đang kết nối" : "API chưa kết nối"}</span><span className="avatar">♟</span></div></header>;
}

export function DashboardShell({ children }: { children: ReactNode }) {
  return <Suspense fallback={<div className="loading-shell">Đang tải dashboard…</div>}><FilterProvider><div className="app-shell"><Sidebar /><div className="main-column"><Header /><main className="main-content">{children}<footer className="page-footer">Chess Visualization <span>•</span> Phân tích dữ liệu ván đấu trực tuyến từ Lichess</footer></main></div></div></FilterProvider></Suspense>;
}
