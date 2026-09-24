import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import type { ProjectsResult } from "../../types/screeningTypes";
import {
  formatPercent,
  muiColorForTone,
  toneForScore,
} from "../../utils/screeningUtils";
import { AssessmentPanel } from "../AssessmentPanel";
import styles from "./ProjectsSection.module.css";

interface ProjectsSectionProps {
  projects: ProjectsResult;
  passingScore: number;
}

export function ProjectsSection({
  projects,
  passingScore,
}: ProjectsSectionProps) {
  return (
    <AssessmentPanel
      id="projects-title"
      kicker="Relevant work"
      title="Projects"
      score={projects.score}
      passingScore={passingScore}
    >
      <div className={styles.list}>
        {projects.matches.map((project) => {
          const tone = toneForScore(project.similarity_score, passingScore);

          return (
            <Card key={project.project_name} className={styles.card}>
              <CardContent className={styles.content}>
                <div className={styles.header}>
                  <div>
                    <Typography component="span" className={styles.dataLabel}>
                      Project
                    </Typography>
                    <Typography component="h3" className={styles.title}>
                      {project.project_name}
                    </Typography>
                  </div>
                  <Chip
                    label={`${formatPercent(project.similarity_score)} match`}
                    color={muiColorForTone(tone)}
                    variant="outlined"
                    className={styles.scoreChip}
                  />
                </div>

                <div className={styles.detailRow}>
                  <Typography component="span" className={styles.dataLabel}>
                    Matched domain
                  </Typography>
                  <Typography component="strong">
                    {project.matched_domain}
                  </Typography>
                </div>

                <div className={styles.evidence}>
                  <Typography component="span" className={styles.dataLabel}>
                    Evidence
                  </Typography>
                  <Typography component="p">{project.evidence}</Typography>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </AssessmentPanel>
  );
}
