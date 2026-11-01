"use client";

import { useEffect, useId, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Info, X } from "lucide-react";
import type { EnsembleAgreementContract } from "@/lib/ensemble-agreement";
import { ARGENTINA_TIME_ZONE_LABEL, formatArgentinaDateTime } from "@/lib/date-time";

const POPOVER_WIDTH = 256;
const EDGE_MARGIN = 8;
const POPOVER_GAP = 8;

function formatCycle(cycle: string): string {
  const match = /^(\d{4})(\d{2})(\d{2})(\d{2})$/.exec(cycle);
  return match ? `GEFS ${match[1]}-${match[2]}-${match[3]} ${match[4]} UTC` : cycle;
}

export function EnsembleAgreementInfo({
  contract,
}: {
  contract: EnsembleAgreementContract | null;
}) {
  const popoverId = useId();
  const modalTitleId = useId();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [mounted, setMounted] = useState(false);
  const [popoverOpen, setPopoverOpen] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [position, setPosition] = useState({ top: 0, left: 0 });

  useEffect(() => setMounted(true), []);

  useEffect(() => () => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
  }, []);

  useLayoutEffect(() => {
    if (!popoverOpen) return;

    const updatePosition = () => {
      const trigger = triggerRef.current;
      const popover = popoverRef.current;
      if (!trigger || !popover) return;

      const triggerRect = trigger.getBoundingClientRect();
      const popoverRect = popover.getBoundingClientRect();
      const left = Math.min(
        Math.max(
          triggerRect.left + triggerRect.width / 2 - popoverRect.width / 2,
          EDGE_MARGIN,
        ),
        window.innerWidth - popoverRect.width - EDGE_MARGIN,
      );
      const fitsBelow =
        triggerRect.bottom + POPOVER_GAP + popoverRect.height <=
        window.innerHeight - EDGE_MARGIN;
      const top = fitsBelow
        ? triggerRect.bottom + POPOVER_GAP
        : Math.max(EDGE_MARGIN, triggerRect.top - POPOVER_GAP - popoverRect.height);

      setPosition({ top, left });
    };

    updatePosition();
    window.addEventListener("resize", updatePosition);
    window.addEventListener("scroll", updatePosition, true);
    return () => {
      window.removeEventListener("resize", updatePosition);
      window.removeEventListener("scroll", updatePosition, true);
    };
  }, [popoverOpen]);

  useEffect(() => {
    if (!modalOpen) return;

    const trigger = triggerRef.current;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setModalOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      trigger?.focus();
    };
  }, [modalOpen]);

  const cancelHide = () => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
  };

  const showPopover = () => {
    cancelHide();
    setPopoverOpen(true);
  };

  const scheduleHide = () => {
    hideTimer.current = setTimeout(() => setPopoverOpen(false), 150);
  };

  const openModal = () => {
    setPopoverOpen(false);
    setModalOpen(true);
  };

  const meta = contract?.metadata;
  const at = (iso: string) => `${formatArgentinaDateTime(iso)} ${ARGENTINA_TIME_ZONE_LABEL}`;

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        aria-label="¿Qué es el acuerdo del ensamble?"
        aria-describedby={popoverOpen ? popoverId : undefined}
        onMouseEnter={showPopover}
        onMouseLeave={scheduleHide}
        onFocus={showPopover}
        onBlur={scheduleHide}
        onClick={showPopover}
        className="inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <Info className="h-3.5 w-3.5" aria-hidden="true" />
      </button>

      {mounted && popoverOpen
        ? createPortal(
            <div
              ref={popoverRef}
              id={popoverId}
              data-testid="ensemble-agreement-popover"
              style={{ top: position.top, left: position.left, width: POPOVER_WIDTH }}
              onMouseEnter={cancelHide}
              onMouseLeave={scheduleHide}
              onFocus={cancelHide}
              onBlur={scheduleHide}
              className="fixed z-[110] max-h-[calc(100vh-1rem)] overflow-y-auto rounded-md border bg-card p-3 text-xs text-card-foreground shadow-lg"
            >
              <p className="leading-relaxed">
                Compara varias simulaciones con distintas condiciones meteorológicas. Un acuerdo
                más alto significa que más simulaciones alcanzan esa zona; no es una certeza de
                que vaya a quemarse. La capa muestra el acuerdo acumulado a un horizonte fijo de
                24 h.
              </p>
              <button
                type="button"
                onClick={openModal}
                className="mt-2 font-medium text-orange-700 underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Ver más
              </button>
            </div>,
            document.body,
          )
        : null}

      {mounted && modalOpen
        ? createPortal(
            <div
              className="fixed inset-0 z-[120] flex items-center justify-center bg-black/45 p-4 backdrop-blur-[1px]"
              onMouseDown={(event) => {
                if (event.target === event.currentTarget) setModalOpen(false);
              }}
            >
              <section
                role="dialog"
                aria-modal="true"
                aria-labelledby={modalTitleId}
                className="w-full max-w-md rounded-xl border bg-card p-5 text-card-foreground shadow-2xl"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-medium uppercase tracking-wide text-orange-700">
                      Capa del mapa
                    </p>
                    <h2 id={modalTitleId} className="mt-1 text-xl font-semibold tracking-tight">
                      Acuerdo del ensamble
                    </h2>
                  </div>
                  <button
                    ref={closeRef}
                    type="button"
                    aria-label="Cerrar"
                    onClick={() => setModalOpen(false)}
                    className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>

                <p className="mt-4 text-sm leading-6 text-muted-foreground">
                  Cada miembro del ensamble simula el mismo incendio con una variante posible del
                  pronóstico meteorológico. Las bandas muestran qué fracción de esos miembros
                  alcanza cada zona: ≥ 0,80 indica mayor coincidencia; ≥ 0,10, una propagación que
                  aparece en menos escenarios.
                </p>

                {meta ? (
                  <dl className="mt-5 grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 border-t pt-4 text-sm">
                    <dt className="text-muted-foreground">Miembros válidos</dt>
                    <dd className="text-right tabular-nums">{meta.valid_members}/{meta.expected_members}</dd>
                    <dt className="text-muted-foreground">Ciclo meteorológico</dt>
                    <dd className="text-right">{formatCycle(meta.weather_cycle)}</dd>
                    <dt className="text-muted-foreground">Inicio</dt>
                    <dd className="text-right">{at(meta.forecast_start)}</dd>
                    <dt className="text-muted-foreground">Horizonte</dt>
                    <dd className="text-right">{meta.horizon_hours} h</dd>
                    <dt className="text-muted-foreground">Vigencia</dt>
                    <dd className="text-right">hasta {at(meta.forecast_valid_at!)}</dd>
                    <dt className="text-muted-foreground">Generado</dt>
                    <dd className="text-right">{at(meta.generated_at)}</dd>
                  </dl>
                ) : (
                  <p className="mt-5 rounded-lg bg-muted px-3 py-2.5 text-sm text-muted-foreground">
                    Activá la capa para consultar los miembros, el ciclo, el horizonte y la
                    vigencia de esta ejecución.
                  </p>
                )}
              </section>
            </div>,
            document.body,
          )
        : null}
    </>
  );
}
