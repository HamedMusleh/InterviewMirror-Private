import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import { Button, Typography } from "@mui/material";

import JobDescriptionDetails from "../../components/JobDescriptionDetails";
import CandidateApplicationPanel from "../../components/CandidateApplicationPanel";
import {
  getJobOpportunity,
  JobApplicationApiError,
  type JobOpportunityResponse,
} from "../../services/jobApplicationApi";
import type { Role } from "../../types/roleTypes";
import styles from "./JobDetailsPage.module.css";

interface JobDetailsPageProps {
  role: Role;
}

/**
 * Job Details page (Task 2): the single destination "View Job
 * Details" now sends every role to, at /jobs/:jobId.
 *
 * The full job description (JobDescriptionDetails) renders exactly
 * the same for recruiters and candidates. Only candidates additionally
 * see CandidateApplicationPanel -- Apply, Check Application Status,
 * screening feedback, and the rest of the application lifecycle.
 * Recruiters never see any of that here.
 */
export default function JobDetailsPage({ role }: JobDetailsPageProps) {
  const { jobId } = useParams<{ jobId: string }>();
  const navigate = useNavigate();

  const [job, setJob] = useState<JobOpportunityResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    if (!jobId) {
      return;
    }

    let cancelled = false;

    async function loadJob() {
      setIsLoading(true);
      setLoadError("");

      try {
        const jobResult = await getJobOpportunity(jobId!);

        if (!cancelled) {
          setJob(jobResult);
        }
      } catch (error) {
        if (!cancelled) {
          setLoadError(
            error instanceof JobApplicationApiError
              ? error.message
              : "Failed to load this job. Please try again.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadJob();

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  if (isLoading) {
    return (
      <main className={styles.page}>
        <Typography color="text.secondary">
          Loading job information...
        </Typography>
      </main>
    );
  }

  if (loadError || !job || !jobId) {
    return (
      <main className={styles.page}>
        <Button
          variant="text"
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/jobs")}
          className={styles.backButton}
        >
          Back to Jobs
        </Button>

        <Typography color="error.main">
          {loadError || "This job could not be found."}
        </Typography>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <Button
        variant="text"
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/jobs")}
        className={styles.backButton}
      >
        Back to Jobs
      </Button>

      <JobDescriptionDetails job={job} />

      {role === "candidate" &&
        (!job.accepting_applications ? (
          /*
           * The server refuses applications to a closed posting, so this
           * is not the guard -- it is the difference between being told
           * and finding out by filling in a form that then fails.
           */
          <div className={styles.applicationSection}>
            <Typography color="text.secondary">
              This job is closed and is no longer accepting applications.
            </Typography>
          </div>
        ) : (
          <div className={styles.applicationSection}>
            <CandidateApplicationPanel
              jobId={jobId}
              jobOpportunityId={job.id}
            />
          </div>
        ))}
    </main>
  );
}
