import { forwardRef } from "react";
import { cn } from "@/lib/utils";

export const Button = forwardRef<HTMLButtonElement, React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "quiet" | "outline" | "danger"; size?: "sm" | "md" | "icon" }>(
  ({ className, variant = "primary", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex cursor-pointer items-center justify-center gap-2 rounded-full font-medium transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--olive)] disabled:pointer-events-none disabled:opacity-40",
        size === "sm" && "min-h-9 px-3 text-xs",
        size === "md" && "min-h-11 px-5 text-sm",
        size === "icon" && "size-10",
        variant === "primary" && "on-ink bg-[var(--ink)] hover:opacity-85",
        variant === "quiet" && "bg-transparent text-[var(--muted)] hover:bg-[var(--surface)] hover:text-[var(--ink)]",
        variant === "outline" && "border border-[var(--line)] bg-[var(--paper)] text-[var(--ink)] hover:border-[var(--ink)]",
        variant === "danger" && "text-red-700 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950/30",
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";
