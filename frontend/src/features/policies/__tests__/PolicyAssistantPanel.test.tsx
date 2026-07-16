import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { policiesApi, type Policy } from "../../../lib/api";
import { PolicyAssistantPanel } from "../PolicyAssistantPanel";

const policy: Pick<Policy, "id" | "name" | "version_label"> = {
  id: "policy-1",
  name: "FY26 travel",
  version_label: "v1",
};

const indexedResponse = {
  policy_id: "policy-1",
  indexing: {
    document_ref: "document-policy-1",
    document_digest: "safe-digest",
    chunk_count: 2,
    injection_flags: [],
  },
};

function renderPanel() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false }, queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PolicyAssistantPanel policy={policy} />
    </QueryClientProvider>,
  );
}

async function openAdvisor(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByRole("button", { name: /policy advisor/i }));
}

async function indexApprovedText(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByLabelText(/approved policy text/i), "Airfare is capped at $500 per trip.");
  await user.click(screen.getByRole("button", { name: /index approved text/i }));
  await screen.findByText(/indexed 2 evidence chunks/i);
}

describe("PolicyAssistantPanel", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(policiesApi, "indexAssistant").mockResolvedValue(indexedResponse);
    vi.spyOn(policiesApi, "askAssistant").mockResolvedValue({
      policy_id: "policy-1",
      answer: {
        answer: "The indexed policy caps airfare at $500 per trip.",
        evidence_found: true,
        citations: [
          {
            document_ref: "document-policy-1",
            source_chunk_id: "chunk-0001",
            excerpt: "Airfare is capped at $500 per trip.",
            similarity: 0.92,
          },
        ],
      },
    });
  });

  it("keeps the RAG source limited to approved policy evidence", async () => {
    const user = userEvent.setup();
    renderPanel();

    await openAdvisor(user);
    expect(screen.getByText(/uploaded text-based PDF and DOCX policy documents are indexed automatically; receipts, reports, and employee data are never included/i)).toBeInTheDocument();
    await indexApprovedText(user);

    await waitFor(() => {
      expect(policiesApi.indexAssistant).toHaveBeenCalledWith("policy-1", "Airfare is capped at $500 per trip.");
    });
    expect(screen.getByLabelText(/approved policy text/i)).toHaveValue("");
  });

  it("shows an advisory answer with its grounded policy evidence", async () => {
    const user = userEvent.setup();
    renderPanel();

    await openAdvisor(user);
    await indexApprovedText(user);
    await user.type(screen.getByLabelText(/question about this policy/i), "What is the airfare cap?");
    await user.click(screen.getByRole("button", { name: /ask policy advisor/i }));

    await waitFor(() => {
      expect(policiesApi.askAssistant).toHaveBeenCalledWith("policy-1", { question: "What is the airfare cap?" });
    });
    expect(await screen.findByText(/the indexed policy caps airfare at \$500/i)).toBeInTheDocument();
    expect(screen.getByText("Grounded evidence")).toBeInTheDocument();
    expect(screen.getByText("Airfare is capped at $500 per trip.")).toBeInTheDocument();
  });

  it("makes insufficient evidence explicit instead of inventing an answer", async () => {
    const user = userEvent.setup();
    vi.mocked(policiesApi.askAssistant).mockResolvedValue({
      policy_id: "policy-1",
      answer: {
        answer: "I do not have sufficient indexed policy evidence to answer that question.",
        evidence_found: false,
        citations: [],
      },
    });
    renderPanel();

    await openAdvisor(user);
    await indexApprovedText(user);
    await user.type(screen.getByLabelText(/question about this policy/i), "What is the hotel cap?");
    await user.click(screen.getByRole("button", { name: /ask policy advisor/i }));

    expect(await screen.findByText(/no grounded evidence was found for this question/i)).toBeInTheDocument();
    expect(screen.queryByText("Grounded evidence")).not.toBeInTheDocument();
  });
});
