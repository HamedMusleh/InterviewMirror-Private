import Typography from "@mui/material/Typography";
import type { ExperienceResult } from "../../types/screeningTypes";
import { AssessmentPanel } from "../AssessmentPanel";
import styles from "./ExperienceSection.module.css";

interface ExperienceSectionProps {
  experience: ExperienceResult;
  passingScore: number;
}

export function ExperienceSection({
  experience,
  passingScore,
}: ExperienceSectionProps) {
  return (
    <AssessmentPanel
      id="experience-title"
      kicker="Work history"
      title="Experience"
      score={experience.score}
      passingScore={passingScore}
    >
      <div className={styles.metricGrid}>
        <MetricTile
          label="Candidate"
          value={`${experience.candidate_years} years`}
        />
        <MetricTile
          label="Required"
          value={`${experience.required_years} years`}
        />
        <MetricTile
          label="Level requirement"
          value={experience.level_match ? "Matched" : "Not matched"}
          status={experience.level_match ? "positive" : "negative"}
          wide
        />
      </div>

      {experience.evidence.length > 0 && (
        <div className={styles.evidence}>
          <Typography component="span" className={styles.dataLabel}>
            Evidence
          </Typography>
          {experience.evidence.map((item) => (
            <Typography component="p" key={item}>
              {item}
            </Typography>
          ))}
        </div>
      )}
    </AssessmentPanel>
  );
}

interface MetricTileProps {
  label: string;
  value: string;
  status?: "positive" | "negative";
  wide?: boolean;
}

function MetricTile({ label, value, status, wide = false }: MetricTileProps) {
  const className = [styles.metricTile, wide ? styles.wide : null]
    .filter(Boolean)
    .join(" ");
  const valueClassName = [
    styles.metricValue,
    status === "positive" ? styles.positive : null,
    status === "negative" ? styles.negative : null,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      <Typography component="span" className={styles.dataLabel}>
        {label}
      </Typography>
      <Typography component="strong" className={valueClassName}>
        {value}
      </Typography>
    </div>
  );
}
