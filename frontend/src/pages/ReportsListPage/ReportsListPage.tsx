import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router";
import {
  Table,
  TableHead,
  TableBody,
  TableRow,
  TableCell,
  Typography,
  Chip,
  Box,
  CircularProgress,
  Alert,
  TextField,
  InputAdornment,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  LinearProgress,
  ButtonBase,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import type { ReportListItem, ReportsListViewState } from "../../types/reportsListTypes";
import { getAllReports } from "../../services/candidateReportListApi";
import {
  RECOMMENDATION_PASS_THRESHOLD,
  SCORE_THRESHOLD_HIGH,
  SCORE_THRESHOLD_MID,
} from "../../components/CandidateReport/const";
import { PAGE_TITLE, EYEBROW_LABEL } from "./const";
import styles from "./ReportsListPage.module.css";

type ScoreFilter = "all" | "high" | "medium" | "low";
type StatusFilter = "all" | "recommended" | "needs_review";
const JOB_FILTER_ALL = "__all__";

function matchesScoreFilter(score: number, filter: ScoreFilter): boolean {
  if (filter === "all") return true;
  if (filter === "high") return score >= SCORE_THRESHOLD_HIGH;
  if (filter === "medium") return score >= SCORE_THRESHOLD_MID && score < SCORE_THRESHOLD_HIGH;
  return score < SCORE_THRESHOLD_MID;
}

function matchesStatusFilter(score: number, filter: StatusFilter): boolean {
  if (filter === "all") return true;
  const isRecommended = score >= RECOMMENDATION_PASS_THRESHOLD;
  return filter === "recommended" ? isRecommended : !isRecommended;
}

function applyFilters(
  items: ReportListItem[],
  query: string,
  scoreFilter: ScoreFilter,
  statusFilter: StatusFilter,
  jobFilter: string
): ReportListItem[] {
  const q = query.trim().toLowerCase();
  return items.filter((item) => {
    const matchesQuery =
      !q || item.candidate_name.toLowerCase().includes(q) || item.job_title.toLowerCase().includes(q);
    const matchesJob = jobFilter === JOB_FILTER_ALL || item.job_title === jobFilter;
    return (
      matchesQuery &&
      matchesJob &&
      matchesScoreFilter(item.overall_score, scoreFilter) &&
      matchesStatusFilter(item.overall_score, statusFilter)
    );
  });
}

export default function ReportsListPage() {
  const navigate = useNavigate();
  const [state, setState] = useState<ReportsListViewState>({ status: "loading" });
  const [query, setQuery] = useState("");
  const [scoreFilter, setScoreFilter] = useState<ScoreFilter>("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [jobFilter, setJobFilter] = useState<string>(JOB_FILTER_ALL);

  useEffect(() => {
    let cancelled = false;
    setState({ status: "loading" });

    getAllReports()
      .then((reports) => {
        if (cancelled) return;
        setState(reports.length === 0 ? { status: "empty" } : { status: "success", data: reports });
      })
      .catch(() => {
        if (cancelled) return;
        setState({ status: "error", message: "Failed to load candidate reports. Please try again." });
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const jobOptions = useMemo(
    () =>
      state.status === "success"
        ? Array.from(new Set(state.data.map((item) => item.job_title))).sort()
        : [],
    [state]
  );

  const filtered = useMemo(
    () =>
      state.status === "success"
        ? applyFilters(state.data, query, scoreFilter, statusFilter, jobFilter)
        : [],
    [state, query, scoreFilter, statusFilter, jobFilter]
  );

  const avgScore = useMemo(
    () =>
      state.status === "success" && state.data.length > 0
        ? Math.round(state.data.reduce((acc, r) => acc + r.overall_score, 0) / state.data.length)
        : 0,
    [state]
  );

  const recommendedCount = useMemo(
    () =>
      state.status === "success"
        ? state.data.filter((r) => r.overall_score >= RECOMMENDATION_PASS_THRESHOLD).length
        : 0,
    [state]
  );

  function openReport(interviewId: number) {
    navigate(`/candidate-report/${interviewId}`);
  }

  return (
    <div className={styles.page}>
      <Typography variant="overline" className={styles.eyebrow}>
        {EYEBROW_LABEL}
      </Typography>
      <Typography variant="h4" className={styles.headline}>
        {PAGE_TITLE}
      </Typography>

      {state.status === "success" && (
        <Box className={styles.statsRow}>
          <Box className={styles.statCard}>
            <Typography variant="h3" fontWeight={700}>
              {state.data.length}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Total Candidates
            </Typography>
          </Box>
          <Box className={styles.statCard}>
            <Typography variant="h3" fontWeight={700} color="success.main">
              {recommendedCount}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Recommended
            </Typography>
          </Box>
          <Box className={styles.statCard}>
            <Typography variant="h3" fontWeight={700}>
              {avgScore}%
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Avg Score
            </Typography>
          </Box>
        </Box>
      )}

      {state.status === "success" && (
        <div className={styles.filterRow}>
          <TextField
            size="small"
            placeholder="Search candidate"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className={styles.searchField}
            slotProps={{
              input: {
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" color="disabled" />
                  </InputAdornment>
                ),
              },
            }}
          />

          <FormControl size="small" className={styles.filterSelect}>
            <InputLabel id="job-filter-label">Role</InputLabel>
            <Select
              labelId="job-filter-label"
              label="Role"
              value={jobFilter}
              onChange={(e) => setJobFilter(e.target.value)}
            >
              <MenuItem value={JOB_FILTER_ALL}>All roles</MenuItem>
              {jobOptions.map((job) => (
                <MenuItem key={job} value={job}>
                  {job}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <FormControl size="small" className={styles.filterSelect}>
            <InputLabel id="score-filter-label">Score</InputLabel>
            <Select
              labelId="score-filter-label"
              label="Score"
              value={scoreFilter}
              onChange={(e) => setScoreFilter(e.target.value as ScoreFilter)}
            >
              <MenuItem value="all">All scores</MenuItem>
              <MenuItem value="high">High ({SCORE_THRESHOLD_HIGH}+)</MenuItem>
              <MenuItem value="medium">
                Medium ({SCORE_THRESHOLD_MID}–{SCORE_THRESHOLD_HIGH - 1})
              </MenuItem>
              <MenuItem value="low">Low (below {SCORE_THRESHOLD_MID})</MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small" className={styles.filterSelect}>
            <InputLabel id="status-filter-label">Status</InputLabel>
            <Select
              labelId="status-filter-label"
              label="Status"
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            >
              <MenuItem value="all">All statuses</MenuItem>
              <MenuItem value="recommended">Recommended</MenuItem>
              <MenuItem value="needs_review">Needs Review</MenuItem>
            </Select>
          </FormControl>
        </div>
      )}

      {state.status === "loading" && (
        <Box className={styles.centerState} data-testid="reports-list-loading">
          <CircularProgress size={28} />
        </Box>
      )}

      {state.status === "error" && (
        <Alert severity="error" data-testid="reports-list-error">
          {state.message}
        </Alert>
      )}

      {state.status === "empty" && (
        <Typography variant="body2" color="text.secondary" data-testid="reports-list-empty">
          No candidate reports available yet.
        </Typography>
      )}

      {state.status === "success" && (
        <div className={styles.tableWrap}>
          {filtered.length === 0 ? (
            <Typography variant="body2" color="text.secondary" className={styles.noResults}>
              No candidates match the current filters.
            </Typography>
          ) : (
            <Table data-testid="reports-list-table">
              <TableHead>
                <TableRow className={styles.headRow}>
                  <TableCell>
                    <Typography variant="overline" color="text.secondary">
                      Candidate
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="overline" color="text.secondary">
                      Role
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="overline" color="text.secondary">
                      Score
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="overline" color="text.secondary">
                      Status
                    </Typography>
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filtered.map((item) => {
                  const isRecommended = item.overall_score >= RECOMMENDATION_PASS_THRESHOLD;
                  const scoreColor =
                    item.overall_score >= SCORE_THRESHOLD_HIGH
                      ? "success"
                      : item.overall_score >= SCORE_THRESHOLD_MID
                        ? "warning"
                        : "error";

                  return (
                    <TableRow
                      key={item.report_id}
                      hover
                      className={styles.bodyRow}
                    >
                      <TableCell>
                        <ButtonBase
                          type="button"
                          className={styles.candidateButton}
                          onClick={() => openReport(item.interview_id)}
                          aria-label={`Open report for ${item.candidate_name}`}
                        >
                          <Typography variant="subtitle1" className={styles.candidateName}>
                            {item.candidate_name}
                          </Typography>
                        </ButtonBase>
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" color="text.secondary">
                          {item.job_title}
                        </Typography>
                      </TableCell>
                      <TableCell className={styles.scoreCell}>
                        <Typography variant="body2" className={styles.scoreText}>
                          {item.overall_score}%
                        </Typography>
                        <LinearProgress
                          variant="determinate"
                          value={item.overall_score}
                          color={scoreColor}
                          className={styles.scoreBar}
                        />
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          label={isRecommended ? "Recommended" : "Needs Review"}
                          color={isRecommended ? "success" : "warning"}
                          variant="outlined"
                          className={styles.statusChip}
                        />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </div>
      )}
    </div>
  );
}
