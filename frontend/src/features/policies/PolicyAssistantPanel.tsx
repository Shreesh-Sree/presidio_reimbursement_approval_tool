import AutoAwesomeOutlinedIcon from "@mui/icons-material/AutoAwesomeOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import MenuBookOutlinedIcon from "@mui/icons-material/MenuBookOutlined";
import PrivacyTipOutlinedIcon from "@mui/icons-material/PrivacyTipOutlined";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { getApiErrorMessage, policiesApi, type Policy, type PolicyAssistantAskResponse, type PolicyAssistantIndexResponse } from "../../lib/api";

type PolicyAssistantPanelProps = {
  policy: Pick<Policy, "id" | "name" | "version_label">;
};

function chunkLabel(count: number) {
  return `${count} evidence ${count === 1 ? "chunk" : "chunks"}`;
}

/**
 * A deliberately explicit, policy-scoped entry point to the isolated RAG
 * assistant. It never reads uploaded documents or report data on its own.
 */
export function PolicyAssistantPanel({ policy }: PolicyAssistantPanelProps) {
  const [policyText, setPolicyText] = useState("");
  const [question, setQuestion] = useState("");
  const [hasExplicitIndex, setHasExplicitIndex] = useState(false);
  const [indexResult, setIndexResult] = useState<PolicyAssistantIndexResponse | null>(null);
  const [answerResult, setAnswerResult] = useState<PolicyAssistantAskResponse | null>(null);

  const indexPolicy = useMutation({
    mutationFn: (content: string) => policiesApi.indexAssistant(policy.id, content),
    onSuccess: (result) => {
      setIndexResult(result);
      setAnswerResult(null);
      setHasExplicitIndex(true);
      // Do not retain a pasted policy in the browser after it has been sent.
      setPolicyText("");
    },
  });

  const askPolicy = useMutation({
    mutationFn: (input: { question: string }) => policiesApi.askAssistant(policy.id, input),
    onSuccess: setAnswerResult,
  });

  const submitIndex = () => {
    const content = policyText.trim();
    if (content) indexPolicy.mutate(content);
  };

  const submitQuestion = () => {
    const trimmedQuestion = question.trim();
    if (trimmedQuestion && hasExplicitIndex) askPolicy.mutate({ question: trimmedQuestion });
  };

  const answer = answerResult?.answer;
  const hasEvidence = answer?.evidence_found ?? false;
  const panelId = `policy-advisor-${policy.id}`;

  return (
    <Accordion disableGutters elevation={0} sx={{ border: 1, borderColor: "divider", borderRadius: "12px !important", overflow: "hidden" }}>
      <AccordionSummary
        aria-controls={`${panelId}-content`}
        expandIcon={<ExpandMoreIcon />}
        id={`${panelId}-header`}
        sx={{ px: 2, "& .MuiAccordionSummary-content": { alignItems: "center", gap: 1.25 } }}
      >
        <AutoAwesomeOutlinedIcon color="primary" fontSize="small" />
        <Box>
          <Typography fontWeight={700} variant="subtitle2">
            Policy advisor
          </Typography>
          <Typography color="text.secondary" variant="caption">
            Grounded Q&amp;A for {policy.version_label}
          </Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails aria-labelledby={`${panelId}-header`} id={`${panelId}-content`} sx={{ px: { xs: 2, sm: 2.5 }, pb: 2.5, pt: 0 }}>
        <Stack spacing={2.25}>
          <Alert icon={<PrivacyTipOutlinedIcon fontSize="inherit" />} severity="info">
            Indexing is explicit. Paste only approved policy text; uploaded files, receipts, report data, and employee details are never sent automatically.
          </Alert>

          <Box>
            <Typography component="h3" fontWeight={700} variant="body2">
              1. Add approved policy evidence
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">
              The text is scoped to this version and cleared from this browser after a successful index.
            </Typography>
          </Box>

          <TextField
            disabled={indexPolicy.isPending}
            fullWidth
            helperText={`${policyText.length.toLocaleString()} / 50,000 characters`}
            inputProps={{ maxLength: 50_000 }}
            label="Approved policy text"
            minRows={6}
            multiline
            onChange={(event) => setPolicyText(event.target.value)}
            placeholder="Paste the policy text that administrators have approved for this version."
            value={policyText}
          />
          <Box>
            <Button
              disabled={!policyText.trim() || indexPolicy.isPending}
              onClick={submitIndex}
              startIcon={indexPolicy.isPending ? <CircularProgress color="inherit" size={16} /> : <MenuBookOutlinedIcon />}
              variant="contained"
            >
              {indexPolicy.isPending ? "Indexing evidence…" : "Index approved text"}
            </Button>
          </Box>

          {indexPolicy.isError && (
            <Alert severity="error">{getApiErrorMessage(indexPolicy.error, "Unable to index approved policy text.")}</Alert>
          )}
          {indexResult && (
            <Alert severity="success">
              Indexed {chunkLabel(indexResult.indexing.chunk_count)} for {policy.version_label}.
            </Alert>
          )}
          {indexResult && indexResult.indexing.injection_flags.length > 0 && (
            <Alert severity="warning">
              Instruction-like content was excluded before indexing. Review the approved source if that was unexpected.
            </Alert>
          )}

          <Divider />

          <Box>
            <Typography component="h3" fontWeight={700} variant="body2">
              2. Ask a policy question
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 0.5 }} variant="body2">
              Answers are advisory only and cannot approve, reject, route, pay, or alter a reimbursement workflow.
            </Typography>
          </Box>

          <TextField
            disabled={!hasExplicitIndex || askPolicy.isPending}
            fullWidth
            helperText={hasExplicitIndex ? "Ask about the policy text indexed above." : "Index approved text above before asking a question."}
            inputProps={{ maxLength: 1_200 }}
            label="Question about this policy"
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="For example: What is the airfare limit?"
            value={question}
          />
          <Box>
            <Button
              disabled={!hasExplicitIndex || !question.trim() || askPolicy.isPending}
              onClick={submitQuestion}
              startIcon={askPolicy.isPending ? <CircularProgress color="inherit" size={16} /> : <AutoAwesomeOutlinedIcon />}
              variant="outlined"
            >
              {askPolicy.isPending ? "Checking evidence…" : "Ask policy advisor"}
            </Button>
          </Box>

          {askPolicy.isError && (
            <Alert severity="error">{getApiErrorMessage(askPolicy.error, "Unable to answer that policy question.")}</Alert>
          )}
          {answer && (
            <Alert aria-live="polite" severity={hasEvidence ? "info" : "warning"}>
              <Typography component="p" sx={{ whiteSpace: "pre-line" }} variant="body2">
                {answer.answer}
              </Typography>
              {!hasEvidence && <Typography sx={{ mt: 1 }} variant="body2">No grounded evidence was found for this question.</Typography>}
            </Alert>
          )}
          {answer && hasEvidence && answer.citations.length > 0 && (
            <Box component="section" aria-label="Grounded policy evidence">
              <Typography component="h4" fontWeight={700} variant="body2">
                Grounded evidence
              </Typography>
              <Stack component="ul" spacing={1.25} sx={{ listStyle: "none", m: 0, mt: 1.25, p: 0 }}>
                {answer.citations.map((citation) => (
                  <Box component="li" key={`${citation.document_ref}-${citation.source_chunk_id}`} sx={{ border: 1, borderColor: "divider", borderRadius: 2, p: 1.25 }}>
                    <Chip label={`Source ${citation.source_chunk_id}`} size="small" />
                    <Typography color="text.secondary" sx={{ mt: 0.75, whiteSpace: "pre-line" }} variant="body2">
                      {citation.excerpt}
                    </Typography>
                  </Box>
                ))}
              </Stack>
            </Box>
          )}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}
