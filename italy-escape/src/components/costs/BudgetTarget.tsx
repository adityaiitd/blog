"use client";

import { Check, TrendingDown } from "lucide-react";
import { useTrip } from "@/components/site/TripProvider";
import { Button } from "@/components/ui/Button";
import { EditableNumber } from "@/components/edit/Editable";
import { fitToTarget, money } from "@/lib/costCalculator";
import { cn } from "@/lib/utils";

export function BudgetTarget({ compact = false }: { compact?: boolean }) {
  const { state, dispatch } = useTrip();
  const status = fitToTarget(state);
  const fill = Math.min(100, status.percentOfTarget);
  return (
    <section className={cn("border-y border-[var(--line)] py-7", compact && "border-t-0 pt-0")}>
      <div className="grid gap-6 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <p className="eyebrow mb-3">Target for two people, everything in</p>
          <div className="flex flex-wrap items-baseline gap-3">
            <p className="font-serif text-6xl">{money(status.total)}</p>
            <span className={cn("rounded-full px-3 py-1 text-xs", status.withinTarget ? "bg-[var(--olive)] text-white" : "bg-[var(--terracotta)] text-white")}>
              {status.withinTarget
                ? `${money(status.target - status.total)} under target`
                : `${money(status.difference)} over target`}
            </span>
          </div>
        </div>
        <label className="grid gap-1 text-[10px] uppercase tracking-wider text-[var(--muted)] lg:justify-items-end">
          Target
          <EditableNumber value={state.budgetTarget} min={0} max={500000} onChange={(value) => dispatch({ type: "set-budget-target", value })} label="Budget target" prefix="$" className="w-40 text-xl" />
        </label>
      </div>
      <div className="mt-5 h-3 overflow-hidden rounded-full bg-[var(--surface)]">
        <div className={cn("h-full transition-all", status.withinTarget ? "bg-[var(--olive)]" : "bg-[var(--terracotta)]")} style={{ width: `${fill}%` }} />
      </div>
      {!compact && (
        <div className="mt-7">
          <p className="eyebrow mb-4">{status.withinTarget ? "Further savings available" : "Ways to get back under target"}</p>
          {status.levers.length === 0 ? (
            <p className="text-sm text-[var(--muted)]">No automatic savings left. Adjust nights, hotels or categories directly.</p>
          ) : (
            <ul className="grid gap-2">
              {status.levers.map((lever) => (
                <li key={lever.id} className="flex flex-wrap items-center justify-between gap-3 border-t border-[var(--line)] py-3">
                  <div>
                    <p className="text-sm font-medium">{lever.label}</p>
                    <p className="text-xs text-[var(--muted)]">{lever.detail}</p>
                  </div>
                  <div className="flex items-center gap-3">
                    <strong className="flex items-center gap-1 text-sm text-[var(--olive)]"><TrendingDown size={14} />{money(lever.savings)}</strong>
                    <Button size="sm" variant="outline" onClick={() => lever.actions.forEach(dispatch)}><Check size={13} />Apply</Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
