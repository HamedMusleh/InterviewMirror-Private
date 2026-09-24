import type { CertificationsResult } from "../../types/screeningTypes";
import { PillVariant } from "../../types/screeningTypes";
import { AssessmentPanel } from "../AssessmentPanel";
import { PillGroup } from "../PillGroup";

interface CertificationsSectionProps {
  certifications: CertificationsResult;
  passingScore: number;
}

export function CertificationsSection({
  certifications,
  passingScore,
}: CertificationsSectionProps) {
  return (
    <AssessmentPanel
      id="certifications-title"
      kicker="Credentials"
      title="Certifications"
      score={certifications.score}
      passingScore={passingScore}
    >
      <PillGroup
        label="Matched"
        values={certifications.matched}
        emptyText="No certifications matched."
        variant={PillVariant.Matched}
      />
      <PillGroup
        label="Missing"
        values={certifications.missing}
        emptyText="No missing certifications."
        variant={PillVariant.Missing}
      />
    </AssessmentPanel>
  );
}
