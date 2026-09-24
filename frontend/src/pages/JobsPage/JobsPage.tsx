import { useEffect, useState } from "react"
import { useNavigate } from "react-router"
import { Tooltip } from "@mui/material"
import ArchiveOutlinedIcon from "@mui/icons-material/ArchiveOutlined"
import BusinessOutlinedIcon from "@mui/icons-material/BusinessOutlined"
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline"
import EditOutlinedIcon from "@mui/icons-material/EditOutlined"
import FactCheckOutlinedIcon from "@mui/icons-material/FactCheckOutlined"
import PeopleOutlineIcon from "@mui/icons-material/PeopleOutline"
import PlaceOutlinedIcon from "@mui/icons-material/PlaceOutlined"
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined"
import UnarchiveOutlinedIcon from "@mui/icons-material/UnarchiveOutlined"
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined"
import WorkOutlineIcon from "@mui/icons-material/WorkOutline"
import {
  deleteJobDescription,
  getJobOpportunities,
  JobApiError,
  setJobStatus,
  type JobOpportunity,
} from "../../services/jobDescriptionApi"
import styles from "./JobsPage.module.css"

type Role = "candidate" | "recruiter";

interface JobsPageProps {
  role: Role;
  onChangeRole: () => void;
  screeningOnly?: boolean;
}

export default function JobsPage({
  role,
  onChangeRole,
  screeningOnly = false,
}: JobsPageProps) {
  const navigate = useNavigate()
  const [jobs, setJobs] = useState<JobOpportunity[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  /*
   * Which job is mid-delete, and anything the server refused to do.
   *
   * The refusal is worth showing verbatim: when a job has applications the
   * server explains how many, and that is the sentence that tells a
   * recruiter why the button did nothing.
   */
  const [deletingJobId, setDeletingJobId] = useState<string | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  /** Which job is mid status change, so its button can say so. */
  const [statusJobId, setStatusJobId] = useState<string | null>(null)

  useEffect(() => {
    async function loadJobs() {
      try {
        const result = await getJobOpportunities(role === "recruiter")
        setJobs(result)
      } catch {
        setError("Unable to load jobs. Please try again.")
      } finally {
        setIsLoading(false)
      }
    }

    loadJobs()
  }, [role])

  const handleToggleArchive = async (job: JobOpportunity) => {
    const closing = job.status !== "archived"

    if (
      closing &&
      !window.confirm(
        `Close "${job.title}"? Candidates will no longer be able to ` +
          "apply. Nothing already submitted is lost, and you can " +
          "reopen it later.",
      )
    ) {
      return
    }

    setDeleteError(null)
    setStatusJobId(job.job_id)

    try {
      const updated = await setJobStatus(
        job.job_id,
        closing ? "archived" : "published",
      )

      setJobs((current) =>
        current.map((item) =>
          item.job_id === job.job_id
            ? { ...item, status: updated.status }
            : item,
        ),
      )
    } catch (caught) {
      setDeleteError(
        caught instanceof JobApiError
          ? caught.message
          : "Unable to change this job's status. Please try again.",
      )
    } finally {
      setStatusJobId(null)
    }
  }

  const handleDelete = async (job: JobOpportunity) => {
    const confirmed = window.confirm(
      `Delete "${job.title}"? This cannot be undone.`,
    )

    if (!confirmed) {
      return
    }

    setDeleteError(null)
    setDeletingJobId(job.job_id)

    try {
      await deleteJobDescription(job.job_id)

      setJobs((current) =>
        current.filter((item) => item.job_id !== job.job_id),
      )
    } catch (caught) {
      setDeleteError(
        caught instanceof JobApiError
          ? caught.message
          : "Unable to delete this job. Please try again.",
      )
    } finally {
      setDeletingJobId(null)
    }
  }

  return (
    <main className={styles.page}>
      <button
        type="button"
        className={styles.backButton}
        onClick={onChangeRole}
      >
        ← Change Role
      </button>
      
      <header className={styles.header}>
        <div>
          <h1>{screeningOnly ? "Screening Results" : "Jobs"}</h1>
          <p>
            {screeningOnly
              ? "Select a job to review candidate screening results."
              : "Explore available opportunities."}
          </p>
        </div>

        {role  === "recruiter" && (
        <button
            type="button"
            className={styles.addButton}
            onClick={() => navigate("/jobs/new")}
        >
            + Add New Job
        </button>
        )}
      </header>

      {isLoading && <p>Loading jobs...</p>}

      {error && <p className={styles.error}>{error}</p>}

      {deleteError && <p className={styles.error}>{deleteError}</p>}

      {!isLoading && !error && jobs.length === 0 && (
        <p>No jobs are available yet.</p>
      )}

      <section className={styles.jobsList}>
        {jobs.map((job) => (
          <article
            key={job.job_id}
            className={`${styles.jobCard} ${
              job.status === "archived" ? styles.jobCardClosed : ""
            }`}
          >
            <div className={styles.jobContent}>
              <div className={styles.titleRow}>
                <h2>{job.title}</h2>

                {job.status === "archived" && (
                  <span className={styles.closedBadge}>Closed</span>
                )}
              </div>

              <p className={styles.meta}>
                <span className={styles.metaItem}>
                  <BusinessOutlinedIcon fontSize="inherit" />
                  {job.department}
                </span>

                <span className={styles.metaItem}>
                  <PlaceOutlinedIcon fontSize="inherit" />
                  {job.location}
                </span>

                <span className={styles.metaItem}>
                  <ScheduleOutlinedIcon fontSize="inherit" />
                  {job.employment_type}
                </span>

                <span className={styles.metaItem}>
                  <WorkOutlineIcon fontSize="inherit" />
                  {job.minimum_years}+ years · {job.experience_level}
                </span>

                {role === "recruiter" && (
                  <span className={styles.metaItem}>
                    <PeopleOutlineIcon fontSize="inherit" />
                    {job.application_count}{" "}
                    {job.application_count === 1
                      ? "applicant"
                      : "applicants"}
                  </span>
                )}
              </p>

              <p className={styles.summary}>{job.job_summary}</p>

              <div className={styles.skills}>
                {job.required_skills.map((skill) => (
                  <span key={skill}>{skill}</span>
                ))}
              </div>
            </div>

            <footer className={styles.cardFooter}>
              <div className={styles.primaryActions}>
                <button
                  type="button"
                  className={styles.viewButton}
                  onClick={() => navigate(`/jobs/${job.job_id}`)}
                >
                  <VisibilityOutlinedIcon fontSize="small" />
                  View details
                </button>

                {role === "recruiter" && (
                  <button
                    type="button"
                    className={styles.screeningButton}
                    onClick={() =>
                      navigate(`/jobs/${job.job_id}/screening-results`)
                    }
                  >
                    <FactCheckOutlinedIcon fontSize="small" />
                    {screeningOnly ? "Open screening" : "Screening results"}
                  </button>
                )}
              </div>

              {/* Changing and destroying the posting, kept apart from the
                  two navigations above so Delete is never the button
                  beside the one people press every time. */}
              {role === "recruiter" && (
                <div className={styles.manageActions}>
                  <Tooltip title="Edit this job">
                    <button
                      type="button"
                      className={styles.iconButton}
                      aria-label="Edit this job"
                      onClick={() => navigate(`/jobs/${job.job_id}/edit`)}
                    >
                      <EditOutlinedIcon fontSize="small" />
                    </button>
                  </Tooltip>

                  <Tooltip
                    title={
                      job.status === "archived"
                        ? "Reopen to applications"
                        : "Close to new applications"
                    }
                  >
                    <span>
                      <button
                        type="button"
                        className={styles.iconButton}
                        aria-label={
                          job.status === "archived"
                            ? "Reopen this job to applications"
                            : "Close this job to new applications"
                        }
                        onClick={() => handleToggleArchive(job)}
                        disabled={statusJobId === job.job_id}
                      >
                        {job.status === "archived" ? (
                          <UnarchiveOutlinedIcon fontSize="small" />
                        ) : (
                          <ArchiveOutlinedIcon fontSize="small" />
                        )}
                      </button>
                    </span>
                  </Tooltip>

                  <span className={styles.actionDivider} aria-hidden="true" />

                  <Tooltip
                    title={
                      job.application_count > 0
                        ? `Cannot delete: ${job.application_count} ` +
                          `candidate${
                            job.application_count === 1 ? " has" : "s have"
                          } applied. Close it instead.`
                        : "Delete this job"
                    }
                  >
                    <span>
                      <button
                        type="button"
                        className={`${styles.iconButton} ${styles.iconButtonDanger}`}
                        aria-label={
                          job.application_count > 0
                            ? "Cannot delete: this job has applications"
                            : "Delete this job"
                        }
                        onClick={() => handleDelete(job)}
                        disabled={
                          deletingJobId === job.job_id ||
                          job.application_count > 0
                        }
                      >
                        <DeleteOutlineIcon fontSize="small" />
                      </button>
                    </span>
                  </Tooltip>
                </div>
              )}
            </footer>
          </article>
        ))}
      </section>
    </main>
  )
}
