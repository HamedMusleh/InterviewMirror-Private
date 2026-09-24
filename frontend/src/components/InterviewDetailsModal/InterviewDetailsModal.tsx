import {
  Dialog,
  DialogTitle,
  DialogContent,
  IconButton,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Typography,
  Chip,
  Stack,
  Box,
  CircularProgress,
  Alert,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import type { InterviewDetailsViewState } from "../../types/interviewDetailsTypes";
import { FOLLOW_UP_LABEL, MODAL_TITLE } from "./const";
import styles from "./InterviewDetailsModal.module.css";

interface InterviewDetailsModalProps {
  open: boolean;
  onClose: () => void;
  state: InterviewDetailsViewState;
}

export default function InterviewDetailsModal({ open, onClose, state }: InterviewDetailsModalProps) {
  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle className={styles.titleRow}>
        {MODAL_TITLE}
        <IconButton onClick={onClose} size="small" aria-label="close">
          <CloseIcon fontSize="small" />
        </IconButton>
      </DialogTitle>

      <DialogContent dividers>
        {state.status === "loading" && (
          <Box className={styles.centerState}>
            <CircularProgress size={28} />
          </Box>
        )}

        {state.status === "error" && <Alert severity="error">{state.message}</Alert>}

        {state.status === "success" && state.data.questions.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            No interview details recorded.
          </Typography>
        )}

        {state.status === "success" &&
          state.data.questions.map((q) => (
            <Accordion key={q.question_id} className={q.is_follow_up ? styles.followUpItem : undefined}>
              <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                <Stack spacing={0.5} className={styles.summaryStack}>
                  <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                    <Chip size="small" label={q.skill} variant="outlined" />
                    {q.is_follow_up && (
                      <Chip size="small" label={FOLLOW_UP_LABEL} color="info" variant="outlined" />
                    )}
                    {q.score !== null && (
                      <Typography variant="caption" color="text.secondary">
                        {q.score}%
                      </Typography>
                    )}
                  </Stack>
                  <Typography variant="body2">{q.question}</Typography>
                </Stack>
              </AccordionSummary>
              <AccordionDetails>
                <Typography variant="body2" color="text.secondary">
                  {q.answer ?? "No answer recorded."}
                </Typography>
                {(q.strengths.length > 0 || q.weaknesses.length > 0) && (
                  <Stack spacing={0.5} mt={1.5}>
                    {q.strengths.map((s, i) => (
                      <Typography key={`s-${i}`} variant="caption" color="success.main">
                        + {s}
                      </Typography>
                    ))}
                    {q.weaknesses.map((w, i) => (
                      <Typography key={`w-${i}`} variant="caption" color="warning.main">
                        − {w}
                      </Typography>
                    ))}
                  </Stack>
                )}
              </AccordionDetails>
            </Accordion>
          ))}
      </DialogContent>
    </Dialog>
  );
}