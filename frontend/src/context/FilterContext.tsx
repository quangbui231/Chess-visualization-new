"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

export type GameType = "all" | "tournament" | "non_tournament";
export type FilterOptions = { speed: string[]; rating_band: string[]; game_type: { value: GameType; label: string }[] };
type FilterState = { speed: string[]; rating_band: string[]; game_type: GameType };
type ContextValue = FilterState & { options: FilterOptions | null; status: "loading" | "ready" | "error"; error: string | null; setFilter: <K extends keyof FilterState>(key: K, value: FilterState[K]) => void; queryString: string };

const defaults: FilterState = { speed: [], rating_band: [], game_type: "all" };
const FilterContext = createContext<ContextValue | null>(null);
const apiBase = (process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");

export function useFilters() {
  const context = useContext(FilterContext);
  if (!context) throw new Error("useFilters must be used within FilterProvider");
  return context;
}

export function FilterProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [status, setStatus] = useState<ContextValue["status"]>("loading");
  const [error, setError] = useState<string | null>(null);
  const speed = searchParams.getAll("speed");
  const rating_band = searchParams.getAll("rating_band");
  const gameTypeValue = searchParams.get("game_type");
  const game_type: GameType = gameTypeValue === "tournament" || gameTypeValue === "non_tournament" ? gameTypeValue : "all";
  const queryString = searchParams.toString();

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${apiBase}/api/filters`, { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) throw new Error(`Không tải được danh sách bộ lọc (${response.status})`);
        return response.json() as Promise<FilterOptions>;
      })
      .then((data) => { setOptions(data); setStatus("ready"); setError(null); })
      .catch((reason: unknown) => {
        if (reason instanceof DOMException && reason.name === "AbortError") return;
        setStatus("error"); setError(reason instanceof Error ? reason.message : "Không thể kết nối API");
      });
    return () => controller.abort();
  }, []);

  const setFilter = useCallback<ContextValue["setFilter"]>((key, value) => {
    const params = new URLSearchParams(searchParams.toString());
    params.delete(key);
    if (key === "speed" || key === "rating_band") {
      for (const selected of value as string[]) params.append(key, selected);
    } else if (value !== defaults.game_type) {
      params.set(key, value as GameType);
    }
    router.replace(`${pathname}${params.size ? `?${params}` : ""}`, { scroll: false });
  }, [pathname, router, searchParams]);

  const value: ContextValue = { speed, rating_band, game_type, options, status, error, setFilter, queryString };
  return <FilterContext.Provider value={value}>{children}</FilterContext.Provider>;
}
