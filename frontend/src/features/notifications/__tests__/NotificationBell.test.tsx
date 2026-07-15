import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { commentsApi, notificationsApi, type Notification } from "../../../lib/api";
import { CommentThread } from "../../../components/CommentThread";
import { NotificationBell } from "../NotificationBell";

function renderWithQuery(children: ReactNode) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return {
    queryClient,
    ...render(<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>),
  };
}

describe("NotificationBell", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(notificationsApi, "list").mockResolvedValue([]);
  });

  it("updates its unread badge when a new notification reaches the query cache", async () => {
    const { queryClient } = renderWithQuery(<NotificationBell />);
    await waitFor(() => expect(notificationsApi.list).toHaveBeenCalled());
    expect(screen.queryByLabelText(/unread notifications/i)).not.toBeInTheDocument();
    const notification: Notification = {
      id: "notice-1",
      title: "Report approved",
      created_at: "2026-08-02T12:00:00Z",
      read_at: null,
    };

    act(() => queryClient.setQueryData(["notifications"], [notification]));

    expect(await screen.findByLabelText("1 unread notifications")).toHaveTextContent("1");
  });
});

describe("CommentThread", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    vi.spyOn(commentsApi, "list").mockResolvedValue([
      { id: "comment-1", body: "Please attach the hotel folio.", visibility: "employee", author_name: "Maya Chen", created_at: "2026-08-02T12:00:00Z" },
    ]);
    vi.spyOn(commentsApi, "create").mockResolvedValue({
      id: "comment-2",
      body: "Folio added to the report.",
      visibility: "employee",
      author_name: "Jordan Lee",
      created_at: "2026-08-02T12:10:00Z",
    });
  });

  it("displays comments and adds a visible reply", async () => {
    const user = userEvent.setup();
    const create = vi.mocked(commentsApi.create);
    renderWithQuery(<CommentThread reportId="report-1" />);

    expect(await screen.findByText(/please attach the hotel folio/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText(/add a comment/i), "Folio added to the report.");
    await user.click(screen.getByRole("button", { name: /post comment/i }));

    await waitFor(() => expect(create).toHaveBeenCalledWith("report-1", "Folio added to the report.", "employee"));
    expect(await screen.findByText("Folio added to the report.")).toBeInTheDocument();
  });
});
