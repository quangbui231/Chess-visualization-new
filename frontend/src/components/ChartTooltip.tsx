"use client";

import { useCallback, useState, type FocusEvent, type PointerEvent, type ReactNode } from "react";

type TooltipState = { text: string; x: number; y: number } | null;

export function ChartTooltip({ children }: { children: ReactNode }) {
  const [tooltip, setTooltip] = useState<TooltipState>(null);

  const show = useCallback((target: EventTarget | null, x: number, y: number) => {
    if (!(target instanceof Element)) return;
    const item = target.closest<HTMLElement | SVGElement>("[data-tooltip]");
    const text = item?.getAttribute("data-tooltip");
    if (!text) {
      setTooltip(null);
      return;
    }
    setTooltip({ text, x: Math.max(12, Math.min(x + 16, window.innerWidth - 280)), y: Math.max(12, Math.min(y + 16, window.innerHeight - 190)) });
  }, []);

  const handlePointerMove = useCallback((event: PointerEvent<HTMLDivElement>) => show(event.target, event.clientX, event.clientY), [show]);
  const handlePointerLeave = useCallback(() => setTooltip(null), []);
  const handleFocus = useCallback((event: FocusEvent<HTMLDivElement>) => {
    if (!(event.target instanceof Element)) return;
    const item = event.target.closest<HTMLElement | SVGElement>("[data-tooltip]");
    if (!item) return;
    const rect = item.getBoundingClientRect();
    show(item, rect.left + rect.width / 2, rect.top);
  }, [show]);

  return <div className="tooltip-surface" onPointerMove={handlePointerMove} onPointerLeave={handlePointerLeave} onFocusCapture={handleFocus} onBlurCapture={handlePointerLeave}>
    {children}
    {tooltip && <div className="chart-tooltip" role="tooltip" style={{ left: tooltip.x, top: tooltip.y }}>{tooltip.text}</div>}
  </div>;
}
