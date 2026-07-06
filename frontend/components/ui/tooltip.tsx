"use client";

import * as React from "react";
import { createPortal } from "react-dom";
import { cn } from "@/lib/utils";

const TOOLTIP_WIDTH = 224;
const GAP = 8;
const EDGE_MARGIN = 8;

export function Tooltip({
  content,
  children,
  className,
}: {
  content: string;
  children: React.ReactNode;
  className?: string;
}) {
  const id = React.useId();
  const triggerRef = React.useRef<HTMLSpanElement>(null);
  const [mounted, setMounted] = React.useState(false);
  const [pos, setPos] = React.useState<{ top: number; left: number } | null>(null);

  React.useEffect(() => setMounted(true), []);

  const show = () => {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (!rect) return;
    const left = Math.min(
      Math.max(rect.left + rect.width / 2 - TOOLTIP_WIDTH / 2, EDGE_MARGIN),
      window.innerWidth - TOOLTIP_WIDTH - EDGE_MARGIN,
    );
    setPos({ top: rect.top - GAP, left });
  };
  const hide = () => setPos(null);

  return (
    <span className={cn("relative inline-flex", className)}>
      <span
        ref={triggerRef}
        tabIndex={0}
        aria-describedby={id}
        className="outline-none"
        onMouseEnter={show}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
      >
        {children}
      </span>
      {mounted && pos
        ? createPortal(
            <span
              id={id}
              role="tooltip"
              style={{ top: pos.top, left: pos.left, width: TOOLTIP_WIDTH }}
              className={cn(
                "pointer-events-none fixed z-[100] -translate-y-full",
                "rounded-md border bg-card px-3 py-2 text-xs text-card-foreground shadow-md",
              )}
            >
              {content}
            </span>,
            document.body,
          )
        : null}
    </span>
  );
}
