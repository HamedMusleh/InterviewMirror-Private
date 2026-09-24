import Button from "@mui/material/Button";
import LinearProgress from "@mui/material/LinearProgress";
import Paper from "@mui/material/Paper";
import Table from "@mui/material/Table";
import TableBody from "@mui/material/TableBody";
import TableCell from "@mui/material/TableCell";
import TableContainer from "@mui/material/TableContainer";
import TableHead from "@mui/material/TableHead";
import TableRow from "@mui/material/TableRow";
import Typography from "@mui/material/Typography";
import type { CandidateSummary } from "../../types/screeningTypes";
import {
  clampScore,
  formatPercent,
  muiColorForStatus,
} from "../../utils/screeningUtils";
import { StatusBadge } from "../StatusBadge";
import styles from "./ScreeningResultsTable.module.css";

interface ScreeningResultsTableProps {
  candidates: CandidateSummary[];
  onSelectCandidate: (applicationId: string) => void;
}

export function ScreeningResultsTable({
  candidates,
  onSelectCandidate,
}: ScreeningResultsTableProps) {
  return (
    <TableContainer component={Paper} className={styles.tableWrap}>
      <Table aria-label="Candidate screening results">
        <TableHead>
          <TableRow>
            <TableCell>Candidate</TableCell>
            <TableCell>Score</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {candidates.map((candidate) => (
            <TableRow key={candidate.applicationId} hover>
              <TableCell>
                <div className={styles.candidateCell}>
                  <Button
                    variant="text"
                    className={styles.candidateButton}
                    onClick={() => onSelectCandidate(candidate.applicationId)}
                  >
                    {candidate.name}
                  </Button>
                  <Typography component="span" className={styles.candidateId}>
                    {candidate.applicationId}
                  </Typography>
                </div>
              </TableCell>
              <TableCell>
                <div className={styles.scoreCell}>
                  <Typography component="span" className={styles.scoreValue}>
                    {formatPercent(candidate.overallScore)}
                  </Typography>
                  <LinearProgress
                    className={styles.scoreProgress}
                    variant="determinate"
                    value={clampScore(candidate.overallScore)}
                    color={muiColorForStatus(candidate.status)}
                    aria-label={`${candidate.name} overall score`}
                  />
                </div>
              </TableCell>
              <TableCell>
                <StatusBadge status={candidate.status} />
              </TableCell>
            </TableRow>
          ))}

          {candidates.length === 0 && (
            <TableRow>
              <TableCell colSpan={3} className={styles.emptyState}>
                No candidates match your search and filters.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
