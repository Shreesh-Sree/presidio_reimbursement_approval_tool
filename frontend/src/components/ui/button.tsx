import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type ButtonVariant = "default" | "outline" | "ghost" | "destructive" | "secondary";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const variants: Record<ButtonVariant, string> = {
  default: "bg-[#00ED64] text-[#001E2B] hover:bg-[#00C956] focus-visible:outline-[#00ED64]",
  outline: "border border-[var(--color-hairline-strong)] bg-[var(--color-canvas)] text-[var(--color-ink)] hover:bg-[var(--color-surface)] dark:border-white/16 dark:bg-[#001E2B] dark:text-[#F9FBFA] dark:hover:bg-[#0D2B36]",
  ghost: "text-[var(--color-ink)] hover:bg-[var(--color-surface)] dark:text-[#F9FBFA] dark:hover:bg-[#0D2B36]",
  destructive: "bg-[#CF4C3A] text-white hover:bg-[#B5382A] focus-visible:outline-[#CF4C3A]",
  secondary: "bg-[#001E2B] text-white hover:bg-[#0D2B36] dark:bg-[#F9FBFA] dark:text-[#001E2B] dark:hover:bg-white",
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
