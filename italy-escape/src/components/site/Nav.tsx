"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Moon, Sun, Undo2, Redo2, Users } from "lucide-react";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/Button";
import { useTrip } from "./TripProvider";
import { cn } from "@/lib/utils";

const links = [
  ["/", "Overview"], ["/itinerary", "Days"], ["/hotels", "Stay"], ["/boats", "At sea"],
  ["/map", "Map"], ["/value", "Save"], ["/costs", "Budget"],
];

export function Nav() {
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();
  const { undo, redo, canUndo, canRedo, peers } = useTrip();
  return (
    <header className="no-print sticky top-0 z-[1000] border-b border-[var(--line)] bg-[color:var(--paper)/.92] backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-[1500px] items-center gap-3 px-4 md:px-8">
        <Link href="/" className="mr-auto font-serif text-lg tracking-wide">Our Italy Escape</Link>
        <nav aria-label="Primary" className="hidden items-center gap-1 lg:flex">
          {links.map(([href, label]) => <Link key={href} href={href} className={cn("rounded-full px-3 py-2 text-xs uppercase tracking-[.14em] text-[var(--muted)] transition hover:text-[var(--ink)]", pathname === href && "bg-[var(--surface)] text-[var(--ink)]")}>{label}</Link>)}
        </nav>
        <div className="flex items-center">
          {peers > 0 && <span className="mr-2 flex items-center gap-1 text-xs text-[var(--olive)]"><Users size={14} />{peers}</span>}
          <Button variant="quiet" size="icon" onClick={undo} disabled={!canUndo} aria-label="Undo"><Undo2 size={16} /></Button>
          <Button variant="quiet" size="icon" onClick={redo} disabled={!canRedo} aria-label="Redo"><Redo2 size={16} /></Button>
          <Button variant="quiet" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle color theme">{theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}</Button>
        </div>
      </div>
      <nav aria-label="Mobile primary" className="flex overflow-x-auto border-t border-[var(--line)] px-3 lg:hidden">
        {links.map(([href, label]) => <Link key={href} href={href} className={cn("shrink-0 px-3 py-2.5 text-xs uppercase tracking-[.12em] text-[var(--muted)]", pathname === href && "text-[var(--ink)] underline underline-offset-4")}>{label}</Link>)}
      </nav>
    </header>
  );
}
