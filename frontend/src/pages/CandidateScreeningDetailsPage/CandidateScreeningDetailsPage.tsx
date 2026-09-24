import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import Button from "@mui/material/Button";
import type { CandidateScreeningDetail } from "../../types/screeningTypes";
import { CandidateSummaryCard } from "../../components/CandidateSummaryCard";
import { CategoryBreakdown } from "../../components/CategoryBreakdown";
import { CertificationsSection } from "../../components/CertificationsSection";
import { CommunicationProfileSection } from "../../components/CommunicationProfileSection";
import { EducationSection } from "../../components/EducationSection";
import { ExperienceSection } from "../../components/ExperienceSection";
import { ProjectsSection } from "../../components/ProjectsSection";
import { SkillsSection } from "../../components/SkillsSection";
import styles from "./CandidateScreeningDetailsPage.module.css";

interface CandidateScreeningDetailsPageProps {
  detail: CandidateScreeningDetail;
  onBack: () => void;
}

export function CandidateScreeningDetailsPage({
  detail,
  onBack,
}: CandidateScreeningDetailsPageProps) {
  const { matching, scoring } = detail;

  return (
    <main className={styles.page}>
      <Button
        variant="text"
        startIcon={<ArrowBackIcon />}
        onClick={onBack}
        className={styles.backButton}
      >
        Back to results
      </Button>

      <CandidateSummaryCard detail={detail} />
      <CategoryBreakdown scoring={scoring} />

      <div className={styles.dashboard}>
        <div className={styles.mainColumn}>
          <SkillsSection
            skills={matching.skills ?? { score: null, status: "not_applicable", required: [], preferred: [] }}
            passingScore={scoring.passing_score}
          />
          <ProjectsSection
            projects={matching.projects ?? { score: null, status: "not_applicable", matches: [] }}
            passingScore={scoring.passing_score}
          />
        </div>

        <aside className={styles.sideColumn} aria-label="Additional screening details">
          <ExperienceSection
            experience={matching.experience ?? { score: null, status: "not_applicable", candidate_years: 0, required_years: 0, level_match: false, evidence: [] }}
            passingScore={scoring.passing_score}
          />
          <EducationSection
            education={matching.education ?? { score: null, status: "not_applicable", matched_field: null, evidence: null }}
            passingScore={scoring.passing_score}
          />
          <CertificationsSection
            certifications={matching.certifications ?? { score: null, status: "not_applicable", matched: [], missing: [] }}
            passingScore={scoring.passing_score}
          />
          <CommunicationProfileSection
            languages={matching.languages ?? { score: null, status: "not_applicable", matched: [], missing: [] }}
            softSkills={matching.soft_skills ?? { score: null, status: "not_applicable", matched: [], missing: [] }}
          />
        </aside>
      </div>
    </main>
  );
}