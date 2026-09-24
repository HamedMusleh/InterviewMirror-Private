import LinearProgress from "@mui/material/LinearProgress";
import Typography from "@mui/material/Typography";
import type { CategoryScore } from "../../types/screeningTypes";
import {
  clampScore,
  formatPercent,
  muiColorForTone,
  toneForScore,
} from "../../utils/screeningUtils";
import styles from "./WeightBar.module.css";

interface WeightBarProps {
  label: string;
  category: CategoryScore;
  passingScore?: number;
  className?: string;
}

export function WeightBar({
  label,
  category,
  passingScore,
  className,
}: WeightBarProps) {
  const tone = toneForScore(category.score, passingScore);
  const rowClassName = [styles.row, className].filter(Boolean).join(" ");

  return (
    <div className={rowClassName}>
      <div className={styles.heading}>
        <Typography component="span" className={styles.label}>
          {label}
        </Typography>
        <Typography component="span" className={styles.score}>
          {formatPercent(category.score)}
        </Typography>
      </div>
      <LinearProgress
        className={styles.progress}
        variant="determinate"
        value={clampScore(category.score)}
        color={muiColorForTone(tone)}
        aria-label={`${label} score`}
      />
      <div className={styles.meta}>
        <span>Weight {formatPercent(category.weight)}</span>
        <span>Weighted score {category.weighted_score}</span>
      </div>
    </div>
  );
}
