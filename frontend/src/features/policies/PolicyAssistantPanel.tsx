import { useMutation } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Minus, Plus, Sparkle } from "@phosphor-icons/react";
import { Button } from "../../components/ui/button";
import { Textarea } from "../../components/ui/textarea";
import { Input } from "../../components/ui/input";
import {
  getApiErrorMessage,
  policiesApi,
  type Policy,
  type PolicyAssistantAskResponse,
  type PolicyAssistantIndexResponse,
} from "../../lib/api";
type Props = { policy: Pick<Policy, "id" | "name" | "version_label" | "document_url" | "assistant_indexing"> };
export function PolicyAssistantPanel({ policy }: Props) {
  const [open, setOpen] = useState(false),
    [policyText, setPolicyText] = useState(""),
    [question, setQuestion] = useState(""),
    [indexed, setIndexed] = useState(false),
    [indexResult, setIndexResult] =
      useState<PolicyAssistantIndexResponse | null>(null),
    [answerResult, setAnswerResult] =
      useState<PolicyAssistantAskResponse | null>(null);
  const index = useMutation({
    mutationFn: (content: string) =>
      policiesApi.indexAssistant(policy.id, content),
    onSuccess: (r) => {
      setIndexResult(r);
      setIndexed(true);
      setPolicyText("");
      setAnswerResult(null);
    },
  });
  const ask = useMutation({
    mutationFn: (input: { question: string }) =>
      policiesApi.askAssistant(policy.id, input),
    onSuccess: setAnswerResult,
  });
  useEffect(() => {
    setIndexed(policy.assistant_indexing?.status === "indexed");
  }, [policy.id, policy.assistant_indexing?.status]);
  const canAsk = indexed || Boolean(policy.document_url);
  const answer = answerResult?.answer;
  return (
    <section className="policy-advisor repl-card">
      <button
        aria-expanded={open}
        className="policy-advisor-head"
        onClick={() => setOpen(!open)}
      >
        <span>
          <b className="advisor-label"><Sparkle aria-hidden size={16} weight="fill" /> Policy advisor <span className="service-tag">AI</span></b>
          <small>Grounded Q&amp;A for {policy.version_label}</small>
        </span>
        <span>{open ? <Minus aria-hidden size={18} weight="bold" /> : <Plus aria-hidden size={18} weight="bold" />}</span>
      </button>
      {open && (
        <div className="policy-advisor-body">
          <div className="repl-alert info">Only approved policy evidence is used. Uploaded text-based PDF and DOCX policy documents are indexed automatically; receipts, reports, and employee data are never included.</div>
          {policy.assistant_indexing?.status === "indexed" && <div className="repl-alert info">The uploaded policy document is ready for grounded questions.</div>}
          {policy.assistant_indexing?.status === "unavailable" && <div className="repl-alert error">{policy.assistant_indexing.message ?? "The uploaded document could not be indexed automatically."}</div>}
          <h3>1. Add approved policy evidence</h3>
          <p>
            The text is scoped to this version and cleared from this browser
            after a successful index.
          </p>
          <label htmlFor="policy-assistant-text">Approved policy text</label>
          <Textarea
            disabled={index.isPending}
            id="policy-assistant-text"
            maxLength={50000}
            onChange={(e) => setPolicyText(e.target.value)}
            placeholder="Paste approved policy text…"
            value={policyText}
          />
          <small>
            {policyText.length.toLocaleString()} / 50,000 characters
          </small>
          <Button
            disabled={!policyText.trim() || index.isPending}
            onClick={() => index.mutate(policyText.trim())}
          >
            {index.isPending ? "Indexing evidence…" : "Index approved text"}
          </Button>
          {index.isError && (
            <div className="repl-alert error">
              {getApiErrorMessage(
                index.error,
                "Unable to index approved policy text.",
              )}
            </div>
          )}
          {indexResult && (
            <div className="repl-alert info">
              Indexed {indexResult.indexing.chunk_count} evidence chunks for{" "}
              {policy.version_label}.
            </div>
          )}
          <hr />
          <h3>2. Ask a policy question</h3>
          <label htmlFor="policy-assistant-question">Question about this policy</label>
          <Input
            disabled={!canAsk || ask.isPending}
            id="policy-assistant-question"
            maxLength={1200}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What is the airfare limit?"
            value={question}
          />
          <Button
            disabled={!canAsk || !question.trim() || ask.isPending}
            onClick={() => ask.mutate({ question: question.trim() })}
            variant="outline"
          >
            {ask.isPending ? "Checking evidence…" : "Ask policy advisor"}
          </Button>
          {ask.isError && (
            <div className="repl-alert error">
              {getApiErrorMessage(
                ask.error,
                "Unable to answer that policy question.",
              )}
            </div>
          )}
          {answer && (
            <div className="repl-alert info">
              <p>{answer.answer}</p>
              {!answer.evidence_found && (
                <p>No grounded evidence was found for this question.</p>
              )}
            </div>
          )}
          {answer?.evidence_found && (
            <>
              <h4>Grounded evidence</h4>
              {answer.citations.map((c) => (
                <article
                  className="citation"
                  key={`${c.document_ref}-${c.source_chunk_id}`}
                >
                  <b>Source {c.source_chunk_id}</b>
                  <p>{c.excerpt}</p>
                </article>
              ))}
            </>
          )}
        </div>
      )}
    </section>
  );
}
