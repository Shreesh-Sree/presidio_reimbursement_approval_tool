import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined";
import { Alert, Box, Button, CircularProgress, Stack, Typography } from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { getApiErrorMessage, reportsApi, type ReceiptAnalysisResponse, type ReportLineItem } from "../../lib/api";

type ReceiptAnalysisPanelProps = {
  reportId: string;
  item: Pick<ReportLineItem, "id" | "receipt">;
};

function resultSeverity(result: ReceiptAnalysisResponse) {
  const findings = result.analysis.findings ?? [];
  if (findings.some((finding) => finding.severity === "error")) return "error" as const;
  if (findings.length > 0) return "warning" as const;
  return "success" as const;
}

/**
 * A human-triggered, metadata-only check. The component intentionally does
 * not request attachments or send receipt URLs/bytes to any service.
 */
export function ReceiptAnalysisPanel({ reportId, item }: ReceiptAnalysisPanelProps) {
  const [result, setResult] = useState<ReceiptAnalysisResponse | null>(null);
  const analyze = useMutation({
    mutationFn: () => reportsApi.analyzeReceipt(reportId, item.id, item.receipt?.id),
    onMutate: () => setResult(null),
    onSuccess: setResult,
  });
  const findings = result?.analysis.findings ?? [];

  return (
    <Box sx={{ mt: 2 }}>
      <Typography color="text.secondary" variant="caption">
        Receipt intelligence is advisory. Only receipt metadata is checked; receipt bytes, file names, links, and report text are not sent.
      </Typography>
      <Box sx={{ mt: 0.75 }}>
        <Button
          disabled={analyze.isPending}
          onClick={() => analyze.mutate()}
          size="small"
          startIcon={analyze.isPending ? <CircularProgress color="inherit" size={15} /> : <FactCheckOutlinedIcon />}
          variant="outlined"
        >
          {analyze.isPending ? "Checking metadata…" : "Check receipt metadata"}
        </Button>
      </Box>

      {analyze.isError && (
        <Alert role="alert" severity="error" sx={{ mt: 1.25 }}>
          {getApiErrorMessage(analyze.error, "Receipt intelligence is unavailable. Complete the usual receipt review.")}
        </Alert>
      )}
      {result && (
        <Alert severity={resultSeverity(result)} sx={{ mt: 1.25 }}>
          {findings.length === 0 ? (
            <Typography component="p" variant="body2">No metadata-based receipt concerns were found.</Typography>
          ) : (
            <Stack component="ul" spacing={0.75} sx={{ listStyle: "none", m: 0, p: 0 }}>
              {findings.map((finding, index) => (
                <Typography component="li" key={`${finding.code}-${index}`} variant="body2">
                  {finding.message ?? finding.code.replace(/_/g, " ")}
                </Typography>
              ))}
            </Stack>
          )}
          {result.analysis.ocr?.performed === false && (
            <Typography component="p" sx={{ mt: 0.75 }} variant="caption">OCR was not performed.</Typography>
          )}
          <Typography component="p" sx={{ mt: 0.75 }} variant="caption">This advisory does not approve, reject, or change this report.</Typography>
        </Alert>
      )}
    </Box>
  );
}
