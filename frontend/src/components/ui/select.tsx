import * as SelectPrimitive from "@radix-ui/react-select";
import { CaretDown, Check } from "@phosphor-icons/react";
import { Children, isValidElement, type ChangeEvent, type FocusEvent, type SelectHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

/**
 * A design-system select with the same small API as a native select. Keeping
 * the option-child API lets existing forms migrate without browser dropdowns.
 */
export function Select({
  "aria-describedby": ariaDescribedBy,
  "aria-invalid": ariaInvalid,
  "aria-label": ariaLabel,
  "aria-labelledby": ariaLabelledBy,
  autoComplete,
  className,
  children,
  disabled,
  form,
  id,
  name,
  onBlur,
  onChange,
  onFocus,
  required,
  tabIndex,
  title,
  value,
}: SelectHTMLAttributes<HTMLSelectElement>) {
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
    <SelectPrimitive.Root
      autoComplete={autoComplete}
      disabled={disabled}
      form={form}
      name={name}
      onValueChange={change}
      required={required}
      value={selectedValue}
    >
      <SelectPrimitive.Trigger
        aria-describedby={ariaDescribedBy}
        aria-invalid={ariaInvalid}
        aria-label={ariaLabel}
        aria-labelledby={ariaLabelledBy}
        className={cn(
          "flex min-h-11 w-full items-center justify-between gap-3 rounded-xl border border-[#d2d2d7] bg-white px-4 py-2.5 text-left text-sm text-[#1d1d1f] outline-none transition-all duration-200 focus:border-[#0071e3] focus:ring-2 focus:ring-[#0071e3]/20 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/12 dark:bg-[#1d1d1f] dark:text-[#f5f5f7] dark:focus:border-[#2997ff] dark:focus:ring-[#2997ff]/20",
          className,
        )}
        id={id}
        onBlur={onBlur ? (event) => onBlur(event as unknown as FocusEvent<HTMLSelectElement>) : undefined}
        onFocus={onFocus ? (event) => onFocus(event as unknown as FocusEvent<HTMLSelectElement>) : undefined}
        tabIndex={tabIndex}
        title={title}
      >
        <SelectPrimitive.Value>{selected?.label}</SelectPrimitive.Value>
        <SelectPrimitive.Icon aria-hidden><CaretDown size={16} weight="bold" /></SelectPrimitive.Icon>
      </SelectPrimitive.Trigger>
      <SelectPrimitive.Portal>
        <SelectPrimitive.Content className="z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-2xl border border-[#d2d2d7] bg-white p-1.5 shadow-lg dark:border-white/12 dark:bg-[#1d1d1f]" position="popper" sideOffset={8}>
          <SelectPrimitive.Viewport>
            {options.map((option) => (
              <SelectPrimitive.Item
                className="relative flex min-h-10 cursor-pointer select-none items-center rounded-xl py-2 pl-9 pr-4 text-sm font-medium text-[#1d1d1f] outline-none data-[highlighted]:bg-[#f5f5f7] data-[state=checked]:bg-[#0071e3] data-[state=checked]:text-white data-[disabled]:pointer-events-none data-[disabled]:opacity-40 dark:text-[#f5f5f7] dark:data-[highlighted]:bg-white/6"
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
