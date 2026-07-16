import * as SelectPrimitive from "@radix-ui/react-select";
import { CaretDown, Check } from "@phosphor-icons/react";
import { Children, isValidElement, type ChangeEvent, type SelectHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

/**
 * A design-system select with the same small API as a native select. Keeping
 * the option-child API lets existing forms migrate without browser dropdowns.
 */
export function Select({ className, children, disabled, id, name, onChange, value }: SelectHTMLAttributes<HTMLSelectElement>) {
  const options = Children.toArray(children).flatMap((child) => {
    if (!isValidElement<{ value?: string; disabled?: boolean; children?: unknown }>(child) || child.type !== "option") return [];
    return [{ disabled: child.props.disabled, label: String(child.props.children ?? ""), value: child.props.value ?? "" }];
  });
  const selectedValue = value == null ? undefined : String(value);
  const selected = options.find((option) => option.value === selectedValue);
  const change = (nextValue: string) => {
    onChange?.({ target: { value: nextValue } } as ChangeEvent<HTMLSelectElement>);
  };

  return (
    <SelectPrimitive.Root disabled={disabled} name={name} onValueChange={change} value={selectedValue}>
      <SelectPrimitive.Trigger
        className={cn(
          "flex min-h-11 w-full items-center justify-between gap-3 rounded-full border border-[#202020]/20 bg-white px-5 py-2.5 text-left text-sm text-[#202020] outline-none transition focus:border-[#202020] focus:ring-2 focus:ring-orange-300 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/20 dark:bg-[#202020] dark:text-[#fcfcfc]",
          className,
        )}
        id={id}
      >
        <SelectPrimitive.Value>{selected?.label}</SelectPrimitive.Value>
        <SelectPrimitive.Icon aria-hidden><CaretDown size={16} weight="bold" /></SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content className="z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-2xl border border-[#202020]/15 bg-white p-1.5 shadow-2xl dark:border-white/15 dark:bg-[#202020]" position="popper" sideOffset={8}>
          <SelectPrimitive.Viewport>
            {options.map((option) => (
              <SelectPrimitive.Item
                className="relative flex min-h-10 cursor-pointer select-none items-center rounded-xl py-2 pl-9 pr-4 text-sm font-medium text-[#202020] outline-none data-[highlighted]:bg-[#f3f0e8] data-[state=checked]:bg-[#ea2804] data-[state=checked]:text-white data-[disabled]:pointer-events-none data-[disabled]:opacity-40 dark:text-[#fcfcfc] dark:data-[highlighted]:bg-white/10"
                disabled={option.disabled}
                key={option.value}
                value={option.value}
              >
                <SelectPrimitive.ItemIndicator className="absolute left-3"><Check size={15} weight="bold" /></SelectPrimitive.ItemIndicator>
                <SelectPrimitive.ItemText>{option.label}</SelectPrimitive.ItemText>
              </SelectPrimitive.Item>
            ))}
          </SelectPrimitive.Viewport>
        </SelectPrimitive.Content>
      </SelectPrimitive.Portal>
    </SelectPrimitive.Root>
  );
}
