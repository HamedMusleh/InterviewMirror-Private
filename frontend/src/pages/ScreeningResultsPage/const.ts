import {
  ScoreFilter,
  ScreeningStatusFilter,
} from "../../types/screeningTypes";

export const SCORE_FILTER_OPTIONS: ReadonlyArray<{
  value: ScoreFilter;
  label: string;
}> = [
  { value: ScoreFilter.All, label: "All scores" },
  { value: ScoreFilter.High, label: "80% and up" },
  { value: ScoreFilter.Medium, label: "50%–79%" },
  { value: ScoreFilter.Low, label: "Below 50%" },
];

export const STATUS_FILTER_OPTIONS: ReadonlyArray<{
  value: ScreeningStatusFilter;
  label: string;
}> = [
  { value: ScreeningStatusFilter.All, label: "All statuses" },
  { value: ScreeningStatusFilter.Recommended, label: "Recommended" },
  { value: ScreeningStatusFilter.Review, label: "Review" },
  { value: ScreeningStatusFilter.Rejected, label: "Rejected" },
];
