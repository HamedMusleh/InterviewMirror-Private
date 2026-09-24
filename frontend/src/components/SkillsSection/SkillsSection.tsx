import Alert from "@mui/material/Alert";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { SkillsResult } from "../../types/screeningTypes";
import { PillVariant } from "../../types/screeningTypes";
import {
  formatPercent,
  muiColorForTone,
  toneForScore,
} from "../../utils/screeningUtils";
import { AssessmentPanel } from "../AssessmentPanel";
import { PillGroup } from "../PillGroup";
import styles from "./SkillsSection.module.css";

interface SkillsSectionProps {
  skills: SkillsResult;
  passingScore: number;
}

export function SkillsSection({ skills, passingScore }: SkillsSectionProps) {
  const missingPreferredSkills = (skills.preferred ?? [])
    .filter((skill) => !skill.matched_skill)
    .map((skill) => skill.preferred_skill);

  return (
    <AssessmentPanel
      id="skills-title"
      kicker="Role requirements"
      title="Skills"
      score={skills.score}
      passingScore={passingScore}
    >
      <div className={styles.list}>
        {skills.required.map((skill) => {
          const tone = toneForScore(skill.similarity_score, passingScore);

          return (
            <Card key={skill.required_skill} className={styles.matchCard}>
              <CardContent className={styles.matchContent}>
                <div className={styles.matchHeader}>
                  <div>
                    <Typography component="span" className={styles.dataLabel}>
                      Required skill
                    </Typography>
                    <Typography component="h3" className={styles.title}>
                      {skill.required_skill}
                    </Typography>
                  </div>
                  <Chip
                    label={`${formatPercent(skill.similarity_score)} match`}
                    color={muiColorForTone(tone)}
                    variant="outlined"
                    className={styles.scoreChip}
                  />
                </div>

                <div className={styles.detailRow}>
                  <Typography component="span" className={styles.dataLabel}>
                    Matched with
                  </Typography>
                  <Typography component="strong">
                    {skill.matched_skill ?? "No match found"}
                  </Typography>
                </div>

                {skill.evidence && (
                  <div className={styles.evidence}>
                    <Typography component="span" className={styles.dataLabel}>
                      Evidence
                    </Typography>
                    <Typography component="p">{skill.evidence}</Typography>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>

      {missingPreferredSkills.length > 0 && (
        <Alert severity="warning" className={styles.alert}>
          <Typography component="strong" className={styles.alertTitle}>
            Missing preferred skills
          </Typography>
          <Typography component="p" className={styles.alertText}>
            These skills were not found in the candidate profile.
          </Typography>
          <PillGroup
            label="Not found"
            values={missingPreferredSkills}
            emptyText="No missing preferred skills."
            variant={PillVariant.Missing}
          />
        </Alert>
      )}
    </AssessmentPanel>
  );
}
