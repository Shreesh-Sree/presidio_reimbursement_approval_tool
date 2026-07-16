export function LumaSpin({ label = "Loading" }: { label?: string }) {
  return <div aria-label={label} className="luma-spin" role="status"><span /><span /></div>;
}

// Compatibility export for the supplied component API.
export const Component = LumaSpin;
