import type { InputHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "min-h-11 w-full rounded-full border border-[#202020]/20 bg-white px-5 py-2.5 text-sm text-[#202020] outline-none placeholder:text-[#8d8d8d] focus:border-[#202020] focus:ring-2 focus:ring-blue-300 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/20 dark:bg-[#202020] dark:text-[#fcfcfc]",
        className,
      )}
      {...props}
    />
  );
}
