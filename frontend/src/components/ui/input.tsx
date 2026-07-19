import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "min-h-11 w-full rounded-xl border border-[#d2d2d7] bg-white px-4 py-2.5 text-sm text-[#1d1d1f] outline-none placeholder:text-[#59595f] focus:border-[#0071e3] focus:ring-2 focus:ring-[#0071e3]/20 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/12 dark:bg-[#1d1d1f] dark:text-[#f5f5f7] dark:focus:border-[#2997ff] dark:focus:ring-[#2997ff]/20",
        className,
      )}
      {...props}
    />
  );
}
