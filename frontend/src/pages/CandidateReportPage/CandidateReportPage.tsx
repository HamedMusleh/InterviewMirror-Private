import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import { Button } from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import CandidateReport from "../../components/CandidateReport";
import InterviewQuestionsSection from "../../components/InterviewQuestionsSection";
import { getCandidateReport } from "../../services/candidateReportApi";
import { getInterviewDetails } from "../../services/interviewDetailsApi";
import type { CandidateReportViewState } from "../../types/candidateReportTypes";
import type { InterviewDetailsViewState } from "../../types/interviewDetailsTypes";
import styles from "./CandidateReportPage.module.css";

export default function CandidateReportPage() {
  const { interviewId } = useParams();
  const navigate = useNavigate();

  const [state, setState] = useState<CandidateReportViewState>({ status: "loading" });
  const [detailsState, setDetailsState] = useState<InterviewDetailsViewState>({ status: "idle" });

  useEffect(() => {
    if (!interviewId) {
      setState({ status: "not_found" });
      setDetailsState({ status: "idle" });
      return;
    }

    let cancelled = false;
    const id = Number(interviewId);

    setState({ status: "loading" });
    setDetailsState({ status: "loading" });

    getCandidateReport(id)
      .then((report) => {
        if (cancelled) return;
        setState(report ? { status: "success", data: report } : { status: "not_found" });
      })
      .catch(() => {
        if (cancelled) return;
        setState({ status: "error", message: "Failed to load candidate report. Please try again." });
      });

    getInterviewDetails(id)
      .then((details) => {
        if (cancelled) return;
        setDetailsState(
          details ? { status: "success", data: details } : { status: "error", message: "No interview details found." }
        );
      })
      .catch(() => {
        if (cancelled) return;
        setDetailsState({ status: "error", message: "Failed to load interview details. Please try again." });
      });

    return () => {
      cancelled = true;
    };
  }, [interviewId]);

  return (
    <div className={styles.page}>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/reports")}
        className={styles.backButton}
      >
        Back to Reports
      </Button>

      <div className={styles.reportCard}>
        <CandidateReport state={state}>
          <InterviewQuestionsSection state={detailsState} />
        </CandidateReport>
      </div>
    </div>
  );
}