import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { rolesApi, usersApi, workflowsApi, type WorkflowRule } from "../../../lib/api";
import { WorkflowRulesPage } from "../WorkflowRulesPage";

const rule: WorkflowRule = {
  id: "workflow-1",
  name: "Large travel escalation",
  conditions: { min_total: 1000, currency_code: "USD" },
  approval_chain: [{ manager_level: 1 }, { role_code: "approver" }],
  priority: 20,
  is_active: true,
};

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <WorkflowRulesPage />
    </QueryClientProvider>,
  );
}

describe("WorkflowRulesPage", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(usersApi, "list").mockResolvedValue([
      { id: "approver-1", email: "morgan@example.com", full_name: "Morgan Manager", status: "active" },
    ]);
    vi.spyOn(rolesApi, "list").mockResolvedValue([
      { code: "approver", name: "Approver" },
      { code: "administrator", name: "Administrator" },
    ]);
    vi.spyOn(workflowsApi, "create").mockResolvedValue(rule);
    vi.spyOn(workflowsApi, "update").mockResolvedValue(rule);
    vi.spyOn(workflowsApi, "remove").mockResolvedValue(undefined);
  });

  it("lists configured routing rules and archives a rule", async () => {
    const user = userEvent.setup();
    vi.spyOn(workflowsApi, "list").mockResolvedValue([rule]);
    const remove = vi.mocked(workflowsApi.remove);
    renderPage();

    expect(await screen.findByText("Large travel escalation")).toBeInTheDocument();
    expect(screen.getByText(/1,000 USD and above/i)).toBeInTheDocument();
    expect(screen.getByText(/manager level 1/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /archive large travel escalation/i }));
    await user.click(within(screen.getByRole("dialog")).getByRole("button", { name: /^archive$/i }));
    await waitFor(() => expect(remove).toHaveBeenCalled());
    expect(remove.mock.calls[0]?.[0]).toBe("workflow-1");
  });

  it("creates a threshold workflow with an ordered manager approval step", async () => {
    const user = userEvent.setup();
    vi.spyOn(workflowsApi, "list").mockResolvedValue([]);
    const create = vi.mocked(workflowsApi.create);
    renderPage();

    await user.click(await screen.findByRole("button", { name: /new workflow rule/i }));
    await user.type(screen.getByLabelText(/rule name/i), "Client travel review");
    await user.type(screen.getByLabelText(/minimum report total/i), "500");
    await user.type(screen.getByLabelText(/currency/i), "usd");
    await user.click(screen.getByRole("button", { name: /save rule/i }));

    await waitFor(() => {
      expect(create).toHaveBeenCalledWith({
        name: "Client travel review",
        conditions: { min_total: 500, currency_code: "USD" },
        approval_chain: [{ manager_level: 1 }],
        priority: 100,
        is_active: true,
      });
    });
  });
});
