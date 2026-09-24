import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { ReactNode } from "react";
import {
  formatPercent,
  muiColorForTone,
  toneForScore,
} from "../../utils/screeningUtils";
import styles from "./AssessmentPanel.module.css";

interface AssessmentPanelProps {
  id: string;
  kicker: string;
  title: string;
  score?: number | null;
  passingScore?: number;
  children: ReactNode;
  className?: string;
}

export function AssessmentPanel({
  id,
  kicker,
  title,
  score,
  passingScore,
  children,
  className,
}: AssessmentPanelProps) {
  const panelClassName = [styles.panel, className].filter(Boolean).join(" ");
  const hasScore = score !== undefined && score !== null;
  const scoreTone = hasScore ? toneForScore(score, passingScore) : null;

  return (
    <Card component="section" className={panelClassName} aria-labelledby={id}>
      <CardContent className={styles.content}>
        <div className={styles.header}>
          <div>
            <Typography component="span" className={styles.kicker}>
              {kicker}
            </Typography>
            <Typography component="h2" id={id} variant="h2">
              {title}
            </Typography>
          </div>
          {hasScore && scoreTone !== null && (
            <Chip
              label={formatPercent(score)}
              color={muiColorForTone(scoreTone)}
              variant="outlined"
              className={styles.score}
            />
          )}
        </div>
        <div className={styles.body}>{children}</div>
      </CardContent>
    </Card>
  );
}