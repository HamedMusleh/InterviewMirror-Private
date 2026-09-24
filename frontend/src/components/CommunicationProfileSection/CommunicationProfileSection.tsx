import type { LanguagesResult, SoftSkillsResult } from "../../types/screeningTypes";
import { PillVariant } from "../../types/screeningTypes";
import { AssessmentPanel } from "../AssessmentPanel";
import { PillGroup } from "../PillGroup";

interface CommunicationProfileSectionProps {
  languages: LanguagesResult;
  softSkills: SoftSkillsResult;
}

export function CommunicationProfileSection({
  languages,
  softSkills,
}: CommunicationProfileSectionProps) {
  return (
    <AssessmentPanel
      id="communication-title"
      kicker="Communication profile"
      title="Languages & Soft Skills"
    >
      <PillGroup
        label="Languages matched"
        values={languages.matched}
        emptyText="No languages matched."
        variant={PillVariant.Matched}
      />
      <PillGroup
        label="Languages missing"
        values={languages.missing}
        emptyText="No missing languages."
        variant={PillVariant.Missing}
      />
      <PillGroup
        label="Soft skills matched"
        values={softSkills.matched}
        emptyText="No soft skills matched."
        variant={PillVariant.Matched}
      />
      <PillGroup
        label="Soft skills missing"
        values={softSkills.missing}
        emptyText="No missing soft skills."
        variant={PillVariant.Missing}
      />
    </AssessmentPanel>
  );
}
