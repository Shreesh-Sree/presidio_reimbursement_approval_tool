import type { TextareaHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "min-h-24 w-full rounded-[10px] border border-[#202020]/20 bg-white px-5 py-3 text-sm text-[#202020] outline-none placeholder:text-[#8d8d8d] focus:border-[#202020] focus:ring-2 focus:ring-blue-300 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/20 dark:bg-[#202020] dark:text-[#fcfcfc]",
        className,
      )}
      {...props}
    />
  );
}
