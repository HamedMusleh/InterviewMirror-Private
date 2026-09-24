import SearchIcon from "@mui/icons-material/Search";
import InputAdornment from "@mui/material/InputAdornment";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Button from "@mui/material/Button";
import { useNavigate } from "react-router";
import { useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import { FilterSelect } from "../../components/FilterSelect";
import { ScreeningResultsTable } from "../../components/ScreeningResultsTable";
import type { CandidateSummary } from "../../types/screeningTypes";
import {
  ScoreFilter,
  ScreeningStatusFilter,
} from "../../types/screeningTypes";
import {
  matchesScoreFilter,
  matchesStatusFilter,
} from "../../utils/screeningUtils";
import {
  SCORE_FILTER_OPTIONS,
  STATUS_FILTER_OPTIONS,
} from "./const";
import styles from "./ScreeningResultsPage.module.css";

interface ScreeningResultsPageProps {
  jobTitle: string;
  candidates: CandidateSummary[];
  onSelectCandidate: (applicationId: string) => void;
}

export function ScreeningResultsPage({
  jobTitle,
  candidates,
  onSelectCandidate,
}: ScreeningResultsPageProps) {
  const navigate = useNavigate();
  const [search, setSearch] = useState("");
  const [scoreFilter, setScoreFilter] = useState(ScoreFilter.All);
  const [statusFilter, setStatusFilter] = useState(ScreeningStatusFilter.All);

  const filteredCandidates = useMemo(() => {
    const query = search.trim().toLowerCase();

    return candidates.filter((candidate) => {
      const matchesSearch =
        query.length === 0 ||
        candidate.name.toLowerCase().includes(query) ||
        candidate.applicationId.toLowerCase().includes(query);

      return (
        matchesSearch &&
        matchesStatusFilter(candidate.status, statusFilter) &&
        matchesScoreFilter(candidate.overallScore, scoreFilter)
      );
    });
  }, [candidates, scoreFilter, search, statusFilter]);

  return (
    <main className={styles.page}>
      <div className={styles.backRow}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/jobs")}
          className={styles.backButton}
        >
          Back to Jobs
        </Button>
      </div>

      <Typography component="span" className={styles.eyebrow}>
        AI Screening Results
      </Typography>
      <Typography component="h1" variant="h1" className={styles.title}>
        Job: {jobTitle}
      </Typography>

      <div className={styles.toolbar}>
        <TextField
          className={styles.search}
          size="small"
          label="Search candidate"
          value={search}
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            setSearch(event.target.value)
          }
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />

        <FilterSelect
          id="score-filter"
          label="Score"
          value={scoreFilter}
          options={SCORE_FILTER_OPTIONS}
          onChange={setScoreFilter}
        />

        <FilterSelect
          id="status-filter"
          label="Status"
          value={statusFilter}
          options={STATUS_FILTER_OPTIONS}
          onChange={setStatusFilter}
        />
      </div>

      <ScreeningResultsTable
        candidates={filteredCandidates}
        onSelectCandidate={onSelectCandidate}
      />
    </main>
  );
}
