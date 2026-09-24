import type { ReactNode } from "react";
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  CircularProgress,
  Alert,
  Chip,
  Stack,
  useTheme,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import EmailOutlinedIcon from "@mui/icons-material/EmailOutlined";
import PhoneOutlinedIcon from "@mui/icons-material/PhoneOutlined";
import type { CandidateReportViewState } from "../../types/candidateReportTypes";
import {
  SCORE_THRESHOLD_HIGH,
  SCORE_THRESHOLD_MID,
  RECOMMENDATION_PASS_THRESHOLD,
  GAUGE_VIEWBOX,
  GAUGE_ARC_PATH,
  GAUGE_STROKE_WIDTH,
  GAUGE_ARC_LENGTH,
} from "./const";
import styles from "./CandidateReport.module.css";

interface CandidateReportProps {
  state: CandidateReportViewState;
  children?: ReactNode;
}

function ScoreGauge({ score }: { score: number }) {
  const theme = useTheme();
  const clamped = Math.max(0, Math.min(100, score));
  const angle = (clamped / 100) * 180;
  const color =
    clamped >= SCORE_THRESHOLD_HIGH
      ? theme.palette.success.main
      : clamped >= SCORE_THRESHOLD_MID
        ? theme.palette.warning.main
        : theme.palette.error.main;

  return (
    <div className={styles.gaugeWrap}>
      <svg viewBox={GAUGE_VIEWBOX} className={styles.gaugeSvg}>
        <path
          d={GAUGE_ARC_PATH}
          fill="none"
          stroke={theme.palette.divider}
          strokeWidth={GAUGE_STROKE_WIDTH}
          strokeLinecap="round"
        />
        <path
          d={GAUGE_ARC_PATH}
          fill="none"
          stroke={color}
          strokeWidth={GAUGE_STROKE_WIDTH}
          strokeLinecap="round"
          strokeDasharray={`${(angle / 180) * GAUGE_ARC_LENGTH} ${GAUGE_ARC_LENGTH}`}
        />
      </svg>
      <div className={styles.gaugeLabel}>
        <Typography component="span" className={styles.gaugeNumber} color="text.primary" fontWeight={700}>
          {Math.round(clamped)}
        </Typography>
        <Typography component="span" className={styles.gaugeUnit} color="text.secondary">
          / 100
        </Typography>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <Box className={styles.centerState} data-testid="report-loading">
      <CircularProgress size={32} />
      <Typography variant="body1" color="text.secondary" mt={2}>
        Loading candidate report...
      </Typography>
    </Box>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <Box className={styles.centerState} data-testid="report-error">
      <Alert severity="error" sx={{ maxWidth: 480 }}>
        Something went wrong while loading the report. {message}
      </Alert>
    </Box>
  );
}

function NotFoundState() {
  return (
    <Box className={styles.centerState} data-testid="report-not-found">
      <Alert severity="info" sx={{ maxWidth: 480 }}>
        No report is available for this interview yet.
      </Alert>
    </Box>
  );
}

function ReportView({
  data,
  children,
}: {
  data: CandidateReportViewState & { status: "success" };
  children?: ReactNode;
}) {
  const { data: report } = data;
  const theme = useTheme();
  const skillEntries = Object.entries(report.skill_scores);
  const isRecommended = report.overall_score >= RECOMMENDATION_PASS_THRESHOLD;

  return (
    <div data-testid="report-content">
      {/* Top row: Overall score | Skill scores | Contact info */}
      <div className={styles.topRow}>
        <Card variant="outlined" className={styles.scoreCard}>
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary" className={styles.sectionLabel}>
              Overall Score
            </Typography>
            <ScoreGauge score={report.overall_score} />
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary" className={styles.sectionLabel}>
              Skill Scores
            </Typography>
            <Stack spacing={2} mt={1.5}>
              {skillEntries.length === 0 ? (
                <Typography variant="body1" color="text.secondary">
                  No skill scores recorded for this interview.
                </Typography>
              ) : (
                skillEntries.map(([skill, score]) => (
                  <Box key={skill}>
                    <Box className={styles.skillRow}>
                      <Typography variant="body1">{skill}</Typography>
                      <Typography variant="body1" fontWeight={600}>
                        {score}%
                      </Typography>
                    </Box>
                    <LinearProgress
                      variant="determinate"
                      value={Math.max(0, Math.min(100, score))}
                      className={styles.skillBar}
                    />
                  </Box>
                ))
              )}
            </Stack>
          </CardContent>
        </Card>

        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary" className={styles.sectionLabel}>
              Contact Info
            </Typography>
            <Stack spacing={1.5} mt={1.5}>
              <Box className={styles.listRow}>
                <EmailOutlinedIcon fontSize="small" color="action" />
                <Typography variant="body1">{report.email}</Typography>
              </Box>
              <Box className={styles.listRow}>
                <PhoneOutlinedIcon fontSize="small" color="action" />
                <Typography variant="body1">{report.phone ?? "Not provided"}</Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      </div>

      <div className={styles.stack}>
        {/* Summary — full width */}
        <Card variant="outlined">
          <CardContent>
            <Typography variant="subtitle2" color="text.secondary" className={styles.sectionLabel}>
              Summary
            </Typography>
            <Typography variant="body1" mt={1}>
              {report.summary}
            </Typography>
          </CardContent>
        </Card>

        {/* Areas for Improvement | Recommendation | Strengths — equal height, color-coded, scrollable */}
        <div className={styles.tripleRow}>
          <Card
            variant="outlined"
            className={styles.accentCard}
            style={{ borderLeftColor: theme.palette.error.main }}
          >
            <CardContent className={styles.accentCardBody}>
              <Typography variant="subtitle2" color="text.secondary" className={styles.sectionLabel}>
                Areas for Improvement
              </Typography>
              {report.areas_for_improvement.length === 0 ? (
                <Typography variant="body1" color="text.secondary" mt={1}>
                  No improvement areas recorded.
                </Typography>
              ) : (
                <Stack spacing={1} mt={1.5}>
                  {report.areas_for_improvement.map((item, i) => (
                    <Box key={i} className={styles.listRow}>
                      <TrendingUpIcon fontSize="small" color="warning" />
                      <Typography variant="body1">{item}</Typography>
                    </Box>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>

          <Card
            variant="outlined"
            className={styles.accentCard}
            style={{ borderLeftColor: isRecommended ? theme.palette.success.main : theme.palette.warning.main }}
          >
            <CardContent className={styles.accentCardBody}>
              <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                <Typography variant="subtitle2" color="text.secondary" className={styles.sectionLabel}>
                  Recommendation
                </Typography>
                <Chip
                  size="small"
                  label={isRecommended ? "Recommended" : "Needs Review"}
                  color={isRecommended ? "success" : "warning"}
                  variant="outlined"
                />
              </Stack>
              <Typography variant="body1">{report.recommendation}</Typography>
            </CardContent>
          </Card>

          <Card
            variant="outlined"
            className={styles.accentCard}
            style={{ borderLeftColor: theme.palette.success.main }}
          >
            <CardContent className={styles.accentCardBody}>
              <Typography variant="subtitle2" color="text.secondary" className={styles.sectionLabel}>
                Strengths
              </Typography>
              {report.strengths.length === 0 ? (
                <Typography variant="body1" color="text.secondary" mt={1}>
                  No strengths recorded.
                </Typography>
              ) : (
                <Stack spacing={1} mt={1.5}>
                  {report.strengths.map((item, i) => (
                    <Box key={i} className={styles.listRow}>
                      <CheckCircleOutlineIcon fontSize="small" color="success" />
                      <Typography variant="body1">{item}</Typography>
                    </Box>
                  ))}
                </Stack>
              )}
            </CardContent>
          </Card>
        </div>

        {children}
      </div>
    </div>
  );
}

function ReportHeader({ candidateName, jobTitle }: { candidateName: string; jobTitle: string }) {
  return (
    <div className={styles.headerRow}>
      <Typography variant="h4" className={styles.pageTitle}>
        Candidate Report
      </Typography>
      <Box className={styles.headerMeta}>
        <Typography variant="h6" fontWeight={700}>
          {candidateName}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {jobTitle}
        </Typography>
      </Box>
    </div>
  );
}

export default function CandidateReport({ state, children }: CandidateReportProps) {
  return (
    <div className={styles.container}>
      {state.status === "success" ? (
        <ReportHeader candidateName={state.data.candidate_name} jobTitle={state.data.job_title} />
      ) : (
        <div className={styles.headerRow}>
          <Typography variant="h4" className={styles.pageTitle}>
            Candidate Report
          </Typography>
        </div>
      )}

      {state.status === "loading" && <LoadingState />}
      {state.status === "error" && <ErrorState message={state.message} />}
      {state.status === "not_found" && <NotFoundState />}
      {state.status === "success" && <ReportView data={state}>{children}</ReportView>}
    </div>
  );
}