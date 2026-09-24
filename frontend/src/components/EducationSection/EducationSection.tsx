import Typography from "@mui/material/Typography";
import type { EducationResult } from "../../types/screeningTypes";
import { AssessmentPanel } from "../AssessmentPanel";
import styles from "./EducationSection.module.css";

interface EducationSectionProps {
  education: EducationResult;
  passingScore: number;
}

export function EducationSection({
  education,
  passingScore,
}: EducationSectionProps) {
  return (
    <AssessmentPanel
      id="education-title"
      kicker="Academic background"
      title="Education"
      score={education.score}
      passingScore={passingScore}
    >
      <Typography component="div" className={styles.highlight}>
        {education.matched_field}
      </Typography>
      <div className={styles.evidence}>
        <Typography component="span" className={styles.dataLabel}>
          Evidence
        </Typography>
        <Typography component="p">{education.evidence}</Typography>
      </div>
    </AssessmentPanel>
  );
}
