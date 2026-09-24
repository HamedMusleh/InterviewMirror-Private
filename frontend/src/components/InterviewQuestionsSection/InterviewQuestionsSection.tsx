import {
  Card,
  CardContent,
  Typography,
  Chip,
  Stack,
  Box,
  CircularProgress,
  Alert,
} from "@mui/material";
import type { InterviewDetailsViewState } from "../../types/interviewDetailsTypes";
import { FOLLOW_UP_LABEL, SECTION_TITLE } from "./const";
import styles from "./InterviewQuestionsSection.module.css";

interface InterviewQuestionsSectionProps {
  state: InterviewDetailsViewState;
}

export default function InterviewQuestionsSection({ state }: InterviewQuestionsSectionProps) {
  if (state.status === "idle") return null;

  return (
    <Card variant="outlined" className={styles.card}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">
          {SECTION_TITLE}
        </Typography>

        {state.status === "loading" && (
          <Box className={styles.centerState} data-testid="details-loading">
            <CircularProgress size={24} />
          </Box>
        )}

        {state.status === "error" && (
          <Alert severity="error" data-testid="details-error" sx={{ mt: 1.5 }}>
            {state.message}
          </Alert>
        )}

        {state.status === "success" && state.data.questions.length === 0 && (
          <Typography variant="body2" color="text.secondary" mt={1.5}>
            No interview questions recorded.
          </Typography>
        )}

        {state.status === "success" &&
          state.data.questions.length > 0 &&
          state.data.questions.map((q) => (
            <Box
              key={q.question_id}
              className={q.is_follow_up ? styles.followUpItem : styles.questionItem}
            >
              <Stack spacing={0.5} className={styles.summaryStack}>
                <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                  {q.skill && <Chip size="small" label={q.skill} variant="outlined" />}
                  {q.is_follow_up && (
                    <Chip size="small" label={FOLLOW_UP_LABEL} color="info" variant="outlined" />
                  )}
                  {q.score !== null && (
                    <Typography variant="body2" color="text.secondary">
                      {q.score}%
                    </Typography>
                  )}
                </Stack>
                <Typography variant="body1" className={styles.questionText}>
                  {q.question}
                </Typography>
              </Stack>

              <Box className={styles.details}>
                <Typography variant="body1" color="text.secondary">
                  {q.answer ?? "No answer recorded."}
                </Typography>

                {(q.relevance_score !== null ||
                  q.correctness_score !== null ||
                  q.depth_score !== null ||
                  q.practicality_score !== null) && (
                  <Stack direction="row" spacing={2} flexWrap="wrap" className={styles.subScores}>
                    {q.relevance_score !== null && (
                      <Typography variant="body2" color="text.secondary">
                        Relevance: {q.relevance_score}
                      </Typography>
                    )}
                    {q.correctness_score !== null && (
                      <Typography variant="body2" color="text.secondary">
                        Correctness: {q.correctness_score}
                      </Typography>
                    )}
                    {q.depth_score !== null && (
                      <Typography variant="body2" color="text.secondary">
                        Depth: {q.depth_score}
                      </Typography>
                    )}
                    {q.practicality_score !== null && (
                      <Typography variant="body2" color="text.secondary">
                        Practicality: {q.practicality_score}
                      </Typography>
                    )}
                  </Stack>
                )}

                {(q.strengths.length > 0 || q.weaknesses.length > 0) && (
                  <Stack spacing={0.5} mt={1.5}>
                    {q.strengths.map((s, i) => (
                      <Typography key={`s-${i}`} variant="body2" color="success.main">
                        + {s}
                      </Typography>
                    ))}
                    {q.weaknesses.map((w, i) => (
                      <Typography key={`w-${i}`} variant="body2" color="warning.main">
                        − {w}
                      </Typography>
                    ))}
                  </Stack>
                )}
              </Box>
            </Box>
          ))}
      </CardContent>
    </Card>
  );
}