import axe from "axe-core";
import { render } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Select } from "../ui/select";

function relativeLuminance(hex: string) {
  const channels = hex.slice(1).match(/../g)?.map((channel) => Number.parseInt(channel, 16) / 255);
  if (!channels || channels.length !== 3) throw new Error(`Expected a six-digit hex colour, received ${hex}.`);
  const [red, green, blue] = channels.map((channel) => (
    channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
  ));
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrastRatio(foreground: string, background: string) {
  const [lighter, darker] = [relativeLuminance(foreground), relativeLuminance(background)].sort((a, b) => b - a);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("frontend accessibility baseline", () => {
  it("keeps global normal-text and destructive-action colours at WCAG AA contrast", () => {
    expect(contrastRatio("#59595f", "#ffffff")).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio("#b42318", "#fff0f0")).toBeGreaterThanOrEqual(4.5);
    expect(contrastRatio("#ffffff", "#c5221f")).toBeGreaterThanOrEqual(4.5);
  });

  it("has no axe violations in the shared required-select and alert pattern", async () => {
    const { container } = render(
      <main>
        <h1>Create workflow rule</h1>
        <form>
          <label htmlFor="approval-role">Approval role</label>
          <Select
            aria-describedby="approval-role-help"
            id="approval-role"
            name="approval_role"
            onChange={vi.fn()}
            required
            value=""
          >
            <option value="">Choose an approval role</option>
            <option value="manager">Manager</option>
          </Select>
          <p id="approval-role-help">Choose the role that approves this workflow step.</p>
          <p role="alert">An approval role is required.</p>
          <button type="submit">Save workflow rule</button>
        </form>
      </main>,
    );

    const results = await axe.run(container, {
      rules: { "color-contrast": { enabled: false } },
    });

    expect(results.violations).toEqual([]);
  });
});
