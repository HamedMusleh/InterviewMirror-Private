import { useEffect, useState } from "react";

import {
  Navigate,
  Route,
  Routes,
  useNavigate,
  useParams,
} from "react-router";

import { CandidateScreeningDetailsPage } from "../../pages/CandidateScreeningDetailsPage";
import CandidateReportPage from "../../pages/CandidateReportPage";
import CreateJobDescriptionPage from "../../pages/CreateJobDescriptionPage/CreateJobDescriptionPage";
import InterviewRoomPage from "../../pages/InterviewRoomPage/InterviewRoomPage";
import JobDetailsPage from "../../pages/JobDetailsPage/JobDetailsPage";
import JobsPage from "../../pages/JobsPage/JobsPage";
import ReportsListPage from "../../pages/ReportsListPage";
import RoleSelectionPage from "../../pages/RoleSelectionPage/RoleSelectionPage";
import { ScreeningResultsPage } from "../../pages/ScreeningResultsPage";
import MicCheckPage from "../../pages/MicCheckPage/MicCheckPage";
import NavBar from "../NavBar/NavBar";

import { getJobOpportunities } from "../../services/jobDescriptionApi";
import {
  getScreeningResultDetail,
  getScreeningResults,
} from "../../services/screeningApi";

import type { Role } from "../../types/roleTypes";
import type {
  CandidateScreeningDetail,
  CandidateSummary,
} from "../../types/screeningTypes";

import styles from "./App.module.css";


function ScreeningResultsRoute() {
  const navigate = useNavigate();
  const { jobId } = useParams();

  const [candidates, setCandidates] = useState<CandidateSummary[]>([]);
  const [jobTitle, setJobTitle] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;

    async function loadResults() {
      setIsLoading(true);
      setError(null);

      try {
        const [results, jobs] = await Promise.all([
          getScreeningResults(jobId!),
          getJobOpportunities(),
        ]);

        const currentJob = jobs.find(
          (job) => job.job_id === jobId,
        );

        if (!cancelled) {
          setCandidates(results);
          setJobTitle(currentJob?.title ?? "Job");
        }
      } catch {
        if (!cancelled) {
          setError(
            "Failed to load screening results. Please try again.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadResults();

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  if (!jobId) {
    return <Navigate replace to="/jobs" />;
  }

  if (isLoading) {
    return (
      <div className={styles.app}>
        Loading screening results…
      </div>
    );
  }

  if (error) {
    return <div className={styles.app}>{error}</div>;
  }

  return (
    <ScreeningResultsPage
      jobTitle={jobTitle}
      candidates={candidates}
      onSelectCandidate={(applicationId) =>
        navigate(
          `/jobs/${jobId}/screening-results/${applicationId}`,
        )
      }
    />
  );
}


function CandidateDetailsRoute() {
  const { jobId, applicationId } = useParams();
  const navigate = useNavigate();

  const [detail, setDetail] =
    useState<CandidateScreeningDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!applicationId) {
      return;
    }

    let cancelled = false;

    async function loadDetail() {
      setIsLoading(true);
      setError(null);

      try {
        const result =
          await getScreeningResultDetail(applicationId!);

        if (!cancelled) {
          setDetail(result);
        }
      } catch {
        if (!cancelled) {
          setError("Failed to load candidate details.");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadDetail();

    return () => {
      cancelled = true;
    };
  }, [applicationId]);

  if (!jobId || !applicationId) {
    return <Navigate replace to="/jobs" />;
  }

  if (isLoading) {
    return (
      <div className={styles.app}>
        Loading candidate details…
      </div>
    );
  }

  if (error || !detail) {
    return (
      <Navigate
        replace
        to={`/jobs/${jobId}/screening-results`}
      />
    );
  }

  return (
    <CandidateScreeningDetailsPage
      detail={detail}
      onBack={() =>
        navigate(`/jobs/${jobId}/screening-results`)
      }
    />
  );
}


function InterviewRoomRoute() {
  const { interviewId } = useParams();

  if (!interviewId) {
    return <Navigate replace to="/screening-results" />;
  }

  return <InterviewRoomPage interviewId={interviewId} />;
}

function MicCheckRoute() {
  const { interviewId } = useParams();
  if (!interviewId) {
    return <Navigate replace to="/screening-results" />;
  }
  return <MicCheckPage />;
}

function CandidateReportRoute() {
  const { interviewId } = useParams();

  if (!interviewId) {
    return <Navigate replace to="/screening-results" />;
  }

  return <CandidateReportPage />;
}


function ReportsListRoute() {
  return <ReportsListPage />;
}


function ApplyRedirectRoute() {
  const { jobId } = useParams();

  return <Navigate replace to={`/jobs/${jobId}`} />;
}


export default function App() {
  const navigate = useNavigate();
  const [role, setRole] = useState<Role | null>(() => {
    const savedRole = sessionStorage.getItem("role");

    return savedRole === "candidate" ||
      savedRole === "recruiter"
      ? savedRole
      : null;
  });

  const handleRoleSelection = (
    selectedRole: Role,
  ) => {
    setRole(selectedRole);
    sessionStorage.setItem("role", selectedRole);
    navigate("/jobs");
  };

  const handleChangeRole = () => {
    setRole(null);
    sessionStorage.removeItem("role");
    navigate("/");
  };

  return (
    <div className={styles.app}>
      <NavBar role={role} onChangeRole={handleChangeRole} />

      <Routes>
        <Route
          index
          element={
            <RoleSelectionPage
              onSelectRole={handleRoleSelection}
            />
          }
        />

        <Route
          path="screening-results"
          element={
            role === "recruiter" ? (
              <JobsPage
                role={role}
                onChangeRole={handleChangeRole}
                screeningOnly
              />
            ) : (
              <Navigate replace to="/jobs" />
            )
          }
        />

        <Route
          path="jobs/:jobId/screening-results"
          element={<ScreeningResultsRoute />}
        />

        <Route
          path="jobs/:jobId/screening-results/:applicationId"
          element={<CandidateDetailsRoute />}
        />

        <Route
          path="interview/:interviewId/check"
          element={<MicCheckRoute />}
        />
        <Route
          path="interview/:interviewId"
          element={<InterviewRoomRoute />}
        />

        <Route
          path="candidate-report/:interviewId"
          element={<CandidateReportRoute />}
        />

        <Route
          path="reports"
          element={<ReportsListRoute />}
        />

        <Route
          path="jobs"
          element={
            role ? (
              <JobsPage
                role={role}
                onChangeRole={handleChangeRole}
              />
            ) : (
              <Navigate replace to="/" />
            )
          }
        />

        <Route
          path="jobs/new"
          element={<CreateJobDescriptionPage />}
        />

        {/* Same page as "new": an edit is the create form with the
            posting already loaded into it. */}
        <Route
          path="jobs/:jobId/edit"
          element={<CreateJobDescriptionPage />}
        />

        <Route
          path="jobs/:jobId"
          element={
            role ? (
              <JobDetailsPage role={role} />
            ) : (
              <Navigate replace to="/" />
            )
          }
        />

        {/* Task 2: "View Job Details" now goes to /jobs/:jobId for
            both roles rather than treating the candidate-application
            route as the main job-details route. This keeps any
            previously bookmarked/shared apply links working. */}
        <Route
          path="jobs/:jobId/apply"
          element={<ApplyRedirectRoute />}
        />

        <Route
          path="*"
          element={<Navigate replace to="/" />}
        />
      </Routes>
    </div>
  );
}