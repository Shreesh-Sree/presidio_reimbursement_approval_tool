import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type ButtonVariant = "default" | "outline" | "ghost" | "destructive" | "secondary";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const variants: Record<ButtonVariant, string> = {
  default: "bg-[#0071e3] text-white hover:bg-[#0077ED] focus-visible:outline-[#0071e3]",
  outline: "border border-[#d2d2d7] bg-white text-[#1d1d1f] hover:bg-[#f5f5f7] dark:border-white/12 dark:bg-[#1d1d1f] dark:text-[#f5f5f7] dark:hover:bg-[#2d2d2d]",
  ghost: "text-[#1d1d1f] hover:bg-[#f5f5f7] dark:text-[#f5f5f7] dark:hover:bg-[#2d2d2d]",
  destructive: "bg-[#ff3b30] text-white hover:bg-[#ff453a] focus-visible:outline-[#ff3b30]",
  secondary: "bg-[#1d1d1f] text-white hover:bg-[#424245] dark:bg-[#f5f5f7] dark:text-[#1d1d1f] dark:hover:bg-white",
};

export function Button({ className, variant = "default", type = "button", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-11 items-center justify-center rounded-full px-5 py-2.5 text-sm font-semibold transition-all duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        className,
      )}
      type={type}
      {...props}
    />
  );
}
