import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { Button } from "../../components/ui/button";
import {
  getApiErrorMessage,
  reportsApi,
  type ReceiptAnalysisResponse,
  type ReportLineItem,
} from "../../lib/api";
type Props = { reportId: string; item: Pick<ReportLineItem, "id" | "receipt"> };
export function ReceiptAnalysisPanel({ reportId, item }: Props) {
  const [result, setResult] = useState<ReceiptAnalysisResponse | null>(null);
  const analyze = useMutation({
    mutationFn: () =>
      reportsApi.analyzeReceipt(reportId, item.id, item.receipt?.id),
    onMutate: () => setResult(null),
    onSuccess: setResult,
  });
  const findings = result?.analysis.findings ?? [];
  return (
    <section className="receipt-advisor">
      <p>
        Receipt intelligence is advisory. Image OCR is performed only on the
        requested supported receipt. For other files, only receipt metadata is
        checked. OCR was not performed for unsupported files; receipt names,
        links, and report text are never sent.
      </p>
      <Button
        disabled={analyze.isPending}
        onClick={() => analyze.mutate()}
        variant="outline"
      >
        {analyze.isPending ? "Checking metadata…" : "Check receipt metadata"}
      </Button>
      {analyze.isError && (
        <div className="repl-alert error">
          {getApiErrorMessage(
            analyze.error,
            "Receipt intelligence is unavailable. Complete the usual receipt review.",
          )}
        </div>
      )}
      {result && (
        <div className="repl-alert info">
          {findings.length ? (
            <ul>
              {findings.map((finding, i) => (
                <li key={`${finding.code}-${i}`}>
                  {finding.message ?? finding.code.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
          ) : (
            "No metadata-based receipt concerns were found."
          )}
          <small>This advisory does not approve, reject, or change this report.</small>
        </div>
      )}
    </section>
  );
}
