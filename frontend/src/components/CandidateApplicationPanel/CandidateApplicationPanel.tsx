import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import {
  Box,
  Button,
  Card,
  CardContent,
  Typography,
} from "@mui/material";

import {
  ALLOWED_RESUME_CONTENT_TYPES,
  MAX_RESUME_FILE_SIZE_BYTES,
  getApplicationStatus,
  submitApplication,
  JobApplicationApiError,
  type ApplicationPageState,
} from "../../services/jobApplicationApi";
import { EmailStatusForm } from "./EmailStatusForm";
import { ApplicationForm } from "./ApplicationForm";
import styles from "./CandidateApplicationPanel.module.css";

interface CandidateApplicationPanelProps {
  jobId: string;
  jobOpportunityId: number;
}

// The one screen this panel is showing right now.
//
// "landing" never assumes a candidate: it is reached on every mount
// with no email involved at all. A specific candidate's identity
// (and their status) is only ever looked up once they type an email
// into the apply form or the check-status form for *that* action --
// never remembered from a previous visit or a previous candidate on
// the same browser (see services/jobApplicationApi.ts).
type Screen = "landing" | "apply" | "check-status" | "result";

type ResultContext =
  // Candidate explicitly asked "Check application status".
  | "checked"
  // Candidate pressed Apply, but the pre-submit check (Task 8) found
  // they already have an application -- no resume was uploaded or
  // screened for this attempt.
  | "duplicate"
  // Candidate's application was just submitted and screened.
  | "submitted";

interface ResultData {
  context: ResultContext;
  state: ApplicationPageState;
  interviewId: number | null;
  email: string;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

// Splits a single "Full Name" field into the first_name/last_name
// pair the backend's User model stores. There is no login flow yet,
// so this typed name (together with the email below) is what creates
// or resolves the candidate's identity on submit.
function splitFullName(fullName: string): {
  firstName: string;
  lastName: string;
} {
  const parts = fullName.trim().split(/\s+/).filter(Boolean);
  const [firstName = "", ...rest] = parts;

  return { firstName, lastName: rest.join(" ") };
}

export default function CandidateApplicationPanel({
  jobId,
  jobOpportunityId,
}: CandidateApplicationPanelProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Whether the job itself is ready to accept applications at all.
  // This is a property of the job, not of any candidate, so it is
  // safe (and useful) to resolve it automatically on mount by asking
  // the status endpoint with no email -- see getApplicationStatus.
  const [isLoadingReadiness, setIsLoadingReadiness] = useState(true);
  const [readinessError, setReadinessError] = useState("");
  const [jobNotReady, setJobNotReady] = useState(false);

  const [screen, setScreen] = useState<Screen>("landing");

  // Apply form fields.
  const [fullName, setFullName] = useState("");
  const [nameError, setNameError] = useState("");
  const [email, setEmail] = useState("");
  const [emailError, setEmailError] = useState("");
  const [phone, setPhone] = useState("");
  const [phoneError, setPhoneError] = useState("");
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState("");

  // "Checking whether you can apply" (Task 8's pre-check) and "your
  // resume is being screened" (Task 3) are two different phases of
  // the same submit action, and get two different messages.
  const [isPrechecking, setIsPrechecking] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  // Check-status form field.
  const [statusEmail, setStatusEmail] = useState("");
  const [statusEmailError, setStatusEmailError] = useState("");
  const [isCheckingStatus, setIsCheckingStatus] = useState(false);
  const [checkStatusError, setCheckStatusError] = useState("");

  const [result, setResult] = useState<ResultData | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadReadiness() {
      setIsLoadingReadiness(true);
      setReadinessError("");

      try {
        // No email passed: this only ever resolves to "job_not_ready"
        // or "can_apply" (see ApplicationStatusService), so it can
        // never leak or assume anything about a specific candidate.
        const status = await getApplicationStatus({ jobId });

        if (!cancelled) {
          setJobNotReady(status.state === "job_not_ready");
        }
      } catch (error) {
        if (!cancelled) {
          setReadinessError(
            error instanceof JobApplicationApiError
              ? error.message
              : "Failed to load this job's application status.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoadingReadiness(false);
        }
      }
    }

    loadReadiness();

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const resetApplyForm = useCallback(() => {
    setFullName("");
    setNameError("");
    setEmail("");
    setEmailError("");
    setPhone("");
    setPhoneError("");
    setResumeFile(null);
    setFileError("");
    setSubmitError("");
  }, []);

  const goToLanding = useCallback(() => {
    setScreen("landing");
    setResult(null);
    setCheckStatusError("");
    setStatusEmailError("");
  }, []);

  const goToApply = useCallback(
    (prefillEmail?: string) => {
      resetApplyForm();

      if (prefillEmail) {
        setEmail(prefillEmail);
      }

      setScreen("apply");
    },
    [resetApplyForm],
  );

  const goToCheckStatus = useCallback(() => {
    setStatusEmail("");
    setStatusEmailError("");
    setCheckStatusError("");
    setScreen("check-status");
  }, []);

  const handleChooseFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const file = event.target.files?.[0];
    event.target.value = "";

    if (!file) {
      return;
    }

    if (!ALLOWED_RESUME_CONTENT_TYPES.includes(file.type)) {
      setFileError("Only PDF files are supported.");
      return;
    }

    if (file.size === 0) {
      setFileError("The selected file is empty.");
      return;
    }

    if (file.size > MAX_RESUME_FILE_SIZE_BYTES) {
      setFileError("File size must not exceed 10 MB.");
      return;
    }

    setFileError("");
    setSubmitError("");
    setResumeFile(file);
  };

  const handleRemoveFile = () => {
    setResumeFile(null);
    setFileError("");
  };

  const handleCheckStatusSubmit = async () => {
    setCheckStatusError("");

    const trimmedEmail = statusEmail.trim();

    if (!trimmedEmail) {
      setStatusEmailError("Email is required.");
      return;
    }

    setStatusEmailError("");
    setIsCheckingStatus(true);

    try {
      const response = await getApplicationStatus({
        jobId,
        email: trimmedEmail,
      });

      setResult({
        context: "checked",
        state: response.state,
        interviewId: response.interview_id,
        email: trimmedEmail,
      });
      setScreen("result");
    } catch (error) {
      setCheckStatusError(
        error instanceof JobApplicationApiError
          ? error.message
          : "Failed to load this job's application status. Please try again.",
      );
    } finally {
      setIsCheckingStatus(false);
    }
  };

  const handleApplySubmit = async () => {
    setSubmitError("");

    const { firstName, lastName } = splitFullName(fullName);
    const trimmedEmail = email.trim();
    const trimmedPhone = phone.trim();

    let hasError = false;

    if (!firstName || !lastName) {
      setNameError("Please enter your first and last name.");
      hasError = true;
    } else {
      setNameError("");
    }

    if (!trimmedEmail) {
      setEmailError("Email is required.");
      hasError = true;
    } else {
      setEmailError("");
    }

    if (!trimmedPhone) {
      setPhoneError("Phone number is required.");
      hasError = true;
    } else {
      setPhoneError("");
    }

    if (!resumeFile) {
      setFileError("Please attach your resume before submitting.");
      hasError = true;
    }

    if (hasError) {
      return;
    }

    // Task 8: check whether this email already has an application
    // for this job *before* uploading/parsing/screening a resume
    // again. The backend status endpoint remains the single source
    // of truth for this decision -- its result is only ever
    // forwarded to the result screen, never re-derived here.
    setIsPrechecking(true);

    let precheck;

    try {
      precheck = await getApplicationStatus({
        jobId,
        email: trimmedEmail,
      });
    } catch (error) {
      setIsPrechecking(false);
      setSubmitError(
        error instanceof JobApplicationApiError
          ? error.message
          : "Failed to check your application status. Please try again.",
      );
      return;
    }

    setIsPrechecking(false);

    if (precheck.state === "job_not_ready") {
      setJobNotReady(true);
      setScreen("landing");
      return;
    }

    if (precheck.state !== "can_apply") {
      // Task 7: the same candidate must not be able to apply twice.
      // An application already exists -- do not run the resume
      // through screening again, just surface the existing state.
      setResult({
        context: "duplicate",
        state: precheck.state,
        interviewId: precheck.interview_id,
        email: trimmedEmail,
      });
      setScreen("result");
      return;
    }

    setIsSubmitting(true);

    try {
      await submitApplication({
        jobOpportunityId,
        firstName,
        lastName,
        email: trimmedEmail,
        phone: trimmedPhone,
        resume: resumeFile!,
      });

      // Re-resolve the page state from the backend rather than
      // guessing locally from the submit response -- this is what
      // surfaces "approved for interview" / "rejected" / "evaluation
      // in progress" correctly (see ApplicationStatusService, the
      // single source of truth for this decision).
      try {
        const finalStatus = await getApplicationStatus({
          jobId,
          email: trimmedEmail,
        });

        setResult({
          context: "submitted",
          state: finalStatus.state,
          interviewId: finalStatus.interview_id,
          email: trimmedEmail,
        });
        setScreen("result");
      } catch {
        // The submission itself succeeded; only the follow-up status
        // lookup failed. Don't fabricate a status -- point the
        // candidate at Check Application Status instead.
        setResult({
          context: "submitted",
          state: "screening_in_progress",
          interviewId: null,
          email: trimmedEmail,
        });
        setScreen("result");
      }
    } catch (error) {
      setSubmitError(
        error instanceof JobApplicationApiError
          ? error.message
          : "Failed to submit your application. Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoadingReadiness) {
    return (
      <Card className={styles.card}>
        <CardContent className={styles.cardContent}>
          <Typography color="text.secondary">
            Loading application options...
          </Typography>
        </CardContent>
      </Card>
    );
  }

  if (readinessError) {
    return (
      <Card className={styles.card}>
        <CardContent className={styles.cardContent}>
          <Typography color="error.main" className={styles.errorText}>
            {readinessError}
          </Typography>
        </CardContent>
      </Card>
    );
  }

  if (jobNotReady) {
    return (
      <Card className={styles.card}>
        <CardContent className={styles.cardContent}>
          <Typography variant="h2" className={styles.title}>
            Application
          </Typography>
          <Typography className={styles.statusMessage}>
            This job is not ready for applications yet.
            <br />
            Please check again later.
          </Typography>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={styles.card}>
      <CardContent className={styles.cardContent}>
        {screen === "landing" && (
          <>
            <Typography variant="h2" className={styles.title}>
              Apply for this Job
            </Typography>
            <Box className={styles.landingActions}>
              <Button
                variant="contained"
                onClick={() => goToApply()}
              >
                Apply for this job
              </Button>
            </Box>

            <Typography className={styles.alreadyAppliedText}>
              Already applied?{" "}
              <Button
                variant="text"
                size="small"
                onClick={goToCheckStatus}
                className={styles.inlineLinkButton}
              >
                Check application status
              </Button>
            </Typography>
          </>
        )}

        {screen === "check-status" && (
          <EmailStatusForm
            title="Check Application Status"
            email={statusEmail}
            emailError={statusEmailError}
            isSubmitting={isCheckingStatus}
            submitError={checkStatusError}
            submitLabel="Check Status"
            onEmailChange={setStatusEmail}
            onSubmit={handleCheckStatusSubmit}
            onBack={goToLanding}
          />
        )}

        {screen === "apply" && (
          <ApplicationForm
            fullName={fullName}
            nameError={nameError}
            email={email}
            emailError={emailError}
            phone={phone}
            phoneError={phoneError}
            resumeFile={resumeFile}
            fileError={fileError}
            isPrechecking={isPrechecking}
            isSubmitting={isSubmitting}
            submitError={submitError}
            fileInputRef={fileInputRef}
            onFullNameChange={setFullName}
            onEmailChange={setEmail}
            onPhoneChange={setPhone}
            onChooseFile={handleChooseFile}
            onFileSelected={handleFileSelected}
            onRemoveFile={handleRemoveFile}
            onSubmit={handleApplySubmit}
            onBack={goToLanding}
            formatFileSize={formatFileSize}
          />
        )}

        {screen === "result" && result && (
          <ResultView
            result={result}
            onCheckDifferentEmail={goToCheckStatus}
            onApplyNow={() => goToApply(result.email)}
            onBack={goToLanding}
          />
        )}
      </CardContent>
    </Card>
  );
}

function ResultView({
  result,
  onCheckDifferentEmail,
  onApplyNow,
  onBack,
}: {
  result: ResultData;
  onCheckDifferentEmail: () => void;
  onApplyNow: () => void;
  onBack: () => void;
}) {
  return (
    <>
      <Typography variant="h2" className={styles.title}>
        Application Status
      </Typography>

      {result.context === "duplicate" && (
        <Typography className={styles.duplicateMessage}>
          You have already applied to this job.
        </Typography>
      )}

      <StatusMessage
        state={result.state}
        interviewId={result.interviewId}
        email={result.email}
        onApplyNow={onApplyNow}
      />

      <Box className={styles.resultActions}>
        <Button variant="text" size="small" onClick={onCheckDifferentEmail}>
          Check a different email
        </Button>
        <Button variant="text" size="small" onClick={onBack}>
          Back
        </Button>
      </Box>
    </>
  );
}

function StatusMessage({
  state,
  interviewId,
  email,
  onApplyNow,
}: {
  state: ApplicationPageState;
  interviewId: number | null;
  email: string;
  onApplyNow: () => void;
}) {
  if (state === "job_not_ready") {
    return (
      <Typography className={styles.statusMessage}>
        This job is not ready for applications yet.
        <br />
        Please check again later.
      </Typography>
    );
  }

  if (state === "can_apply") {
    return (
      <>
        <Typography className={styles.statusMessage}>
          We couldn't find an application for {email} on this job yet.
        </Typography>
        <Box className={styles.resultActions}>
          <Button variant="contained" onClick={onApplyNow}>
            Apply for this job
          </Button>
        </Box>
      </>
    );
  }

  if (state === "screening_in_progress") {
    return (
      <Typography className={styles.statusMessage}>
        Your resume is currently in the screening phase.
        <br />
        Please wait until the screening process is finished.
      </Typography>
    );
  }

  if (state === "approved_for_interview") {
    return (
      <ApprovedForInterview interviewId={interviewId} />
    );
  }

  if (state === "rejected") {
    return (
      <Typography className={styles.rejectedMessage}>
        Your application did not pass the screening phase.
        <br />
        You cannot continue to the interview for this job.
      </Typography>
    );
  }

  // state === "evaluation_in_progress"
  return (
    <>
      <Typography className={styles.statusMessage}>
        Your interview is currently in the evaluation phase.
      </Typography>
      <Typography className={styles.statusMessage}>
        You cannot submit another application for this job.
        <br />
        Please choose another job.
      </Typography>
    </>
  );
}

function ApprovedForInterview({
  interviewId,
}: {
  interviewId: number | null;
}) {
  const navigate = useNavigate();

  return (
    <>
      <Box className={styles.successMessage}>
        <CheckCircleIcon color="success" fontSize="small" />
        <Typography color="success.main">
          Your application passed the screening phase.
        </Typography>
      </Box>

      {interviewId ? (
        <Box className={styles.resultActions}>
          <Button
            variant="contained"
            onClick={() => navigate(`/interview/${interviewId}/check`)}
          >
            Join Interview
          </Button>
        </Box>
      ) : (
        <Typography className={styles.statusMessage}>
          Your interview is being prepared. Please check back shortly.
        </Typography>
      )}
    </>
  );
}
