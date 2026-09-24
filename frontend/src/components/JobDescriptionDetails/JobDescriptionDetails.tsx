import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";

import type { JobOpportunityResponse } from "../../services/jobApplicationApi";

import styles from "./JobDescriptionDetails.module.css";

interface JobDescriptionDetailsProps {
  job: JobOpportunityResponse;
}

function ChipSection({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <>
      <Typography variant="h2" className={styles.sectionTitle}>
        {title}
      </Typography>
      <Stack
        direction="row"
        spacing={1}
        useFlexGap
        flexWrap="wrap"
        className={styles.chips}
      >
        {items.map((item) => (
          <Chip key={item} label={item} />
        ))}
      </Stack>
    </>
  );
}

function ListSection({
  title,
  items,
}: {
  title: string;
  items: string[];
}) {
  if (items.length === 0) {
    return null;
  }

  return (
    <>
      <Typography variant="h2" className={styles.sectionTitle}>
        {title}
      </Typography>
      <ul className={styles.list}>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </>
  );
}

/**
 * Renders the complete candidate-visible job description: every field
 * a recruiter entered when creating the job that a candidate is
 * allowed to see, with empty/unset fields simply omitted.
 *
 * Deliberately role-agnostic -- JobDetailsPage renders this component
 * identically for recruiters and candidates. It never renders
 * recruiter-only or internal fields (e.g. passing score, recruiter
 * id): those are not even present on the JobOpportunityResponse type
 * this component receives, so there is nothing to accidentally leak.
 */
export default function JobDescriptionDetails({
  job,
}: JobDescriptionDetailsProps) {
  const hasExperienceInfo =
    job.experience_level.trim().length > 0 || job.minimum_years > 0;

  return (
    <Card className={styles.card}>
      <CardContent className={styles.cardContent}>
        <Typography variant="h1" className={styles.jobTitle}>
          {job.title}
        </Typography>

        <Typography color="text.secondary" className={styles.jobMeta}>
          {job.department} • {job.employment_type} • {job.location}
        </Typography>

        <Typography variant="h2" className={styles.sectionTitleFirst}>
          About the Role
        </Typography>
        <Typography className={styles.jobSummary}>
          {job.job_summary}
        </Typography>

        <ListSection
          title="Responsibilities"
          items={job.responsibilities}
        />

        <ChipSection title="Required Skills" items={job.required_skills} />

        <ChipSection
          title="Preferred Skills"
          items={job.preferred_skills}
        />

        {hasExperienceInfo && (
          <>
            <Typography variant="h2" className={styles.sectionTitle}>
              Experience
            </Typography>
            <Typography className={styles.experienceText}>
              {[
                job.experience_level.trim() || null,
                job.minimum_years > 0
                  ? `${job.minimum_years}+ years`
                  : null,
              ]
                .filter(Boolean)
                .join(" · ")}
            </Typography>
          </>
        )}

        <ListSection title="Education" items={job.education} />

        <ListSection title="Certifications" items={job.certifications} />

        <ChipSection title="Languages" items={job.languages} />

        <ChipSection
          title="Technical Stack"
          items={job.technical_stack}
        />

        <ChipSection title="Soft Skills" items={job.soft_skills} />
      </CardContent>
    </Card>
  );
}
