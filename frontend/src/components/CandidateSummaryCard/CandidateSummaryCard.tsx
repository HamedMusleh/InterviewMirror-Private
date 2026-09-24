import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Typography from "@mui/material/Typography";
import type { CandidateScreeningDetail } from "../../types/screeningTypes";
import { formatPercent } from "../../utils/screeningUtils";
import { ScoreRing, ScoreRingSize } from "../ScoreRing";
import { StatusBadge } from "../StatusBadge";
import styles from "./CandidateSummaryCard.module.css";

interface CandidateSummaryCardProps {
  detail: CandidateScreeningDetail;
}

export function CandidateSummaryCard({ detail }: CandidateSummaryCardProps) {
  const { scoring } = detail;

  return (
    <Card component="header" className={styles.card}>
      <CardContent className={styles.content}>
        <div className={styles.info}>
          <Typography component="span" className={styles.eyebrow}>
            Candidate Screening Details
          </Typography>
          <Typography component="h1" variant="h1" className={styles.name}>
            {detail.name}
          </Typography>

          <div className={styles.metaGrid}>
            <MetaItem label="Candidate ID" value={detail.applicationId} />
            <MetaItem label="Job ID" value={detail.jobId} />
            <div className={styles.metaItem}>
              <span>Status</span>
              <StatusBadge status={scoring.final_status} />
            </div>
            <MetaItem
              label="Passing score"
              value={formatPercent(scoring.passing_score)}
            />
          </div>
        </div>

        <div className={styles.scoreArea}>
          <ScoreRing
            score={scoring.overall_score}
            passingScore={scoring.passing_score}
            size={ScoreRingSize.Medium}
            label="Overall"
          />
          <Typography component="span" className={styles.caption}>
            {formatPercent(scoring.overall_score)} overall match
          </Typography>
        </div>
      </CardContent>
    </Card>
  );
}

interface MetaItemProps {
  label: string;
  value: string;
}

function MetaItem({ label, value }: MetaItemProps) {
  return (
    <div className={styles.metaItem}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
