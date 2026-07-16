import { LumaSpin } from "./luma-spin";

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return <div aria-live="polite" className="flex min-h-28 items-center justify-center"><LumaSpin label={label} /></div>;
}
