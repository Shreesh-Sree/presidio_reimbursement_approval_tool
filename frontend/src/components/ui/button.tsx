import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

type ButtonVariant = "default" | "outline" | "ghost" | "destructive" | "secondary";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
};

const variants: Record<ButtonVariant, string> = {
  default: "bg-[#ea2804] text-white hover:bg-[#c01f00] focus-visible:outline-[#ea2804]",
  outline: "border border-[#202020] bg-white text-[#202020] hover:bg-[#f3f0e8] dark:border-[#fcfcfc] dark:bg-[#202020] dark:text-[#fcfcfc] dark:hover:bg-[#303030]",
  ghost: "text-[#202020] hover:bg-[#f3f0e8] dark:text-[#fcfcfc] dark:hover:bg-[#303030]",
  destructive: "bg-orange-600 text-white hover:bg-orange-500 focus-visible:outline-orange-600",
  secondary: "bg-[#202020] text-[#fcfcfc] hover:bg-[#3a3a3a] dark:bg-[#f3f0e8] dark:text-[#202020] dark:hover:bg-white",
};

export function Button({ className, variant = "default", type = "button", ...props }: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex min-h-11 items-center justify-center rounded-full px-5 py-2.5 text-sm font-bold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variants[variant],
        className,
      )}
      type={type}
      {...props}
    />
  );
}
