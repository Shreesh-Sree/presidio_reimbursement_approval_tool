import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "./ui/button";
import { LoadingState } from "./ui/loading-state";
import { Form, FormField } from "./ui/form";
import { Label } from "./ui/label";
import { Select } from "./ui/select";
import { Textarea } from "./ui/textarea";
import { commentsApi, type ReportComment } from "../lib/api";

type CommentThreadProps = {
  reportId: string;
};

function displayVisibility(visibility: string) {
  return visibility === "internal" ? "Internal" : visibility === "employee" ? "Employee-visible" : "Visible to all";
}

export function CommentThread({ reportId }: CommentThreadProps) {
  const queryClient = useQueryClient();
  const [body, setBody] = useState("");
  const [visibility, setVisibility] = useState<ReportComment["visibility"]>("employee");
  const comments = useQuery({ queryKey: ["report", reportId, "comments"], queryFn: () => commentsApi.list(reportId) });
  const addComment = useMutation({
    mutationFn: () => commentsApi.create(reportId, body.trim(), visibility),
    onSuccess: (comment) => {
      queryClient.setQueryData<ReportComment[]>(["report", reportId, "comments"], (current) => [...(current ?? []), comment]);
      setBody("");
    },
  });

  return (
    <section aria-labelledby="comments-heading" className="space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <div>
        <h2 className="font-semibold text-slate-950 dark:text-white" id="comments-heading">Comments</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">Share context with the employee or keep an internal note for approvers.</p>
      </div>
      {comments.isLoading && <LoadingState label="Loading comments" />}
      {comments.isError && <p className="text-sm text-orange-600">Unable to load comments.</p>}
      {comments.data?.length === 0 && <p className="text-sm text-slate-600 dark:text-slate-300">No comments yet.</p>}
      <div className="space-y-3">
        {comments.data?.map((comment) => (
          <article className="rounded-lg bg-slate-50 p-3 dark:bg-slate-800/70" key={comment.id}>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-500 dark:text-slate-400">
              <span className="font-semibold text-slate-700 dark:text-slate-200">{comment.author_name ?? "Team member"}</span>
              <span>{displayVisibility(comment.visibility)}</span>
              <time dateTime={comment.created_at}>{new Date(comment.created_at).toLocaleString()}</time>
            </div>
            <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-100">{comment.body}</p>
          </article>
        ))}
      </div>
      <Form
        className="border-t border-slate-200 pt-4 dark:border-slate-800"
        onSubmit={(event) => {
          event.preventDefault();
          if (body.trim()) addComment.mutate();
        }}
      >
        <FormField>
          <Label htmlFor={`report-comment-${reportId}`}>Add a comment</Label>
          <Textarea id={`report-comment-${reportId}`} onChange={(event) => setBody(event.target.value)} placeholder="Write a clear, actionable comment" value={body} />
        </FormField>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <FormField className="w-full sm:max-w-52">
            <Label htmlFor={`comment-visibility-${reportId}`}>Visibility</Label>
            <Select id={`comment-visibility-${reportId}`} onChange={(event) => setVisibility(event.target.value as ReportComment["visibility"])} value={visibility}>
              <option value="employee">Employee-visible</option>
              <option value="internal">Internal approver note</option>
              <option value="all">Visible to all</option>
            </Select>
          </FormField>
          <Button disabled={!body.trim() || addComment.isPending} type="submit">{addComment.isPending ? "Posting…" : "Post comment"}</Button>
        </div>
        {addComment.isError && <p className="text-sm text-orange-600">Unable to post this comment.</p>}
      </Form>
    </section>
  );
}
