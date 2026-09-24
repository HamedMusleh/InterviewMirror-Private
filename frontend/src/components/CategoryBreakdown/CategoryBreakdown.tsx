import Typography from "@mui/material/Typography";
import { CATEGORY_LABELS, CATEGORY_ORDER } from "./const";
import type { ScoringResponse } from "../../types/screeningTypes";
import { WeightBar } from "../WeightBar";
import styles from "./CategoryBreakdown.module.css";

interface CategoryBreakdownProps {
  scoring: ScoringResponse;
}

export function CategoryBreakdown({ scoring }: CategoryBreakdownProps) {
  return (
    <section className={styles.section} aria-labelledby="category-breakdown-title">
      <div className={styles.heading}>
        <Typography component="h2" variant="h2" id="category-breakdown-title">
          Category Breakdown
        </Typography>
        <Typography component="p">
          Performance by category, including each category&apos;s scoring weight.
        </Typography>
      </div>

      <div className={styles.grid}>
        {CATEGORY_ORDER.map((categoryKey) => (
          <WeightBar
            key={categoryKey}
            label={CATEGORY_LABELS[categoryKey]}
            category={scoring.category_breakdown[categoryKey]}
            passingScore={scoring.passing_score}
          />
        ))}
      </div>
    </section>
  );
}
