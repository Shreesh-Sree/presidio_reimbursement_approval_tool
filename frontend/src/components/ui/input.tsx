import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "h-11 w-full rounded-lg border border-[var(--color-hairline-strong)] bg-[var(--color-canvas)] px-4 py-2.5 text-sm text-[var(--color-ink)] outline-none placeholder:text-[var(--color-steel)] focus:border-[#00684A] focus:ring-2 focus:ring-[#00ED64]/15 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/16 dark:bg-[#0D2B36] dark:text-[#F9FBFA] dark:focus:border-[#00ED64] dark:focus:ring-[#00ED64]/20",
        className,
      )}
      {...props}
    />
  );
}
