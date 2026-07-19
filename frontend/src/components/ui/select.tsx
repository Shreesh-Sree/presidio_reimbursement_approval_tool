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
          "flex h-11 w-full items-center justify-between gap-3 rounded-lg border border-[var(--color-hairline-strong)] bg-[var(--color-canvas)] px-4 py-2.5 text-left text-sm text-[var(--color-ink)] outline-none transition-all duration-150 focus:border-[#00684A] focus:ring-2 focus:ring-[#00ED64]/15 disabled:cursor-not-allowed disabled:opacity-50 dark:border-white/16 dark:bg-[#0D2B36] dark:text-[#F9FBFA] dark:focus:border-[#00ED64] dark:focus:ring-[#00ED64]/20",
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
        <SelectPrimitive.Content className="z-50 max-h-72 min-w-[var(--radix-select-trigger-width)] overflow-hidden rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-1.5 shadow-lg dark:border-white/10 dark:bg-[#001E2B]" position="popper" sideOffset={8}>
          <SelectPrimitive.Viewport>
            {options.map((option) => (
              <SelectPrimitive.Item
                className="relative flex min-h-10 cursor-pointer select-none items-center rounded-lg py-2 pl-9 pr-4 text-sm font-medium text-[var(--color-ink)] outline-none data-[highlighted]:bg-[var(--color-surface)] data-[state=checked]:bg-[#00ED64] data-[state=checked]:text-[#001E2B] data-[disabled]:pointer-events-none data-[disabled]:opacity-40 dark:text-[#F9FBFA] dark:data-[highlighted]:bg-[#0D2B36]"
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
