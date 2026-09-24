import CircularProgress from "@mui/material/CircularProgress";
import Typography from "@mui/material/Typography";
import { ScoreTone } from "../../types/screeningTypes";
import {
  clampScore,
  formatPercent,
  muiColorForTone,
  toneForScore,
} from "../../utils/screeningUtils";
import styles from "./ScoreRing.module.css";
import { ScoreRingSize } from "./ScoreRing.types";

interface ScoreRingProps {
  score: number;
  passingScore?: number;
  size?: ScoreRingSize;
  label?: string;
  className?: string;
}

export function ScoreRing({
  score,
  passingScore,
  size = ScoreRingSize.Medium,
  label = "Overall",
  className,
}: ScoreRingProps) {
  const clampedScore = clampScore(score);
  const tone = toneForScore(clampedScore, passingScore);
  const rootClassName = [styles.root, styles[size], className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={rootClassName}>
      <meter
        className={styles.semanticMeter}
        min={0}
        max={100}
        value={clampedScore}
        aria-label={`${label} score ${formatPercent(clampedScore)}`}
      />
      <CircularProgress
        className={styles.track}
        variant="determinate"
        value={100}
        size="100%"
        thickness={4}
      />
      <CircularProgress
        className={styles.progress}
        variant="determinate"
        value={clampedScore}
        size="100%"
        thickness={4}
        color={muiColorForTone(tone)}
      />
      <div className={styles.value}>
        <Typography
          component="span"
          className={`${styles.number} ${toneClassName(tone)}`}
        >
          {formatPercent(clampedScore)}
        </Typography>
        <Typography component="span" className={styles.label}>
          {label}
        </Typography>
      </div>
    </div>
  );
}

function toneClassName(tone: ScoreTone): string {
  switch (tone) {
    case ScoreTone.Good:
      return styles.good;
    case ScoreTone.Warning:
      return styles.warning;
    case ScoreTone.Bad:
      return styles.bad;
  }
}
