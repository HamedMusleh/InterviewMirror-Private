import { ScreeningStatus } from "../../types/screeningTypes";

export const SCREENING_STATUS_LABELS: Record<ScreeningStatus, string> = {
  [ScreeningStatus.Recommended]: "Recommended",
  [ScreeningStatus.Review]: "Review",
  [ScreeningStatus.Rejected]: "Rejected",
};
