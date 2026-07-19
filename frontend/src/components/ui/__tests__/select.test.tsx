import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Select } from "../select";

describe("Select", () => {
  it("forwards native form validation and accessible trigger properties", () => {
    const onChange = vi.fn();
    const { container } = render(
      <form id="workflow-form">
        <label htmlFor="workflow-approver">Approver</label>
        <Select
          aria-describedby="workflow-approver-help"
          aria-invalid="true"
          id="workflow-approver"
          name="approver_id"
          onChange={onChange}
          required
          value=""
        >
          <option value="">Choose an approver</option>
          <option value="user-1">Avery Singh</option>
        </Select>
        <p id="workflow-approver-help">An approver is required.</p>
      </form>,
    );

    const trigger = screen.getByRole("combobox", { name: "Approver" });
    expect(trigger).toHaveAttribute("aria-describedby", "workflow-approver-help");
    expect(trigger).toHaveAttribute("aria-invalid", "true");

    const nativeSelect = container.querySelector("select[name=approver_id]");
    expect(nativeSelect).toHaveAttribute("required");
    expect((container.querySelector("form") as HTMLFormElement).checkValidity()).toBe(false);
  });
});
