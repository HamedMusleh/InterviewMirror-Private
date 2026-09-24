import {
  ScoreFilter,
  ScoreTone,
  ScreeningStatus,
  ScreeningStatusFilter,
} from "../types/screeningTypes";

const DEFAULT_PASSING_SCORE = 70;

export type MuiFeedbackColor = "success" | "warning" | "error";

export function clampScore(score: number): number {
  return Math.max(0, Math.min(100, score));
}

export function formatScore(score: number): string {
  return Number.isInteger(score) ? String(score) : score.toFixed(2);
}

export function formatPercent(score: number): string {
  return `${formatScore(score)}%`;
}

export function toneForScore(
  score: number,
  passingScore = DEFAULT_PASSING_SCORE,
): ScoreTone {
  if (score >= passingScore) return ScoreTone.Good;
  if (score >= passingScore - 15) return ScoreTone.Warning;
  return ScoreTone.Bad;
}

export function toneForStatus(status: ScreeningStatus): ScoreTone {
  switch (status) {
    case ScreeningStatus.Recommended:
      return ScoreTone.Good;
    case ScreeningStatus.Review:
      return ScoreTone.Warning;
    case ScreeningStatus.Rejected:
      return ScoreTone.Bad;
  }
}

export function muiColorForTone(tone: ScoreTone): MuiFeedbackColor {
  switch (tone) {
    case ScoreTone.Good:
      return "success";
    case ScoreTone.Warning:
      return "warning";
    case ScoreTone.Bad:
      return "error";
  }
}

export function muiColorForStatus(
  status: ScreeningStatus,
): MuiFeedbackColor {
  return muiColorForTone(toneForStatus(status));
}

export function matchesScoreFilter(
  score: number,
  filter: ScoreFilter,
): boolean {
  switch (filter) {
    case ScoreFilter.All:
      return true;
    case ScoreFilter.High:
      return score >= 80;
    case ScoreFilter.Medium:
      return score >= 50 && score < 80;
    case ScoreFilter.Low:
      return score < 50;
  }
}

export function matchesStatusFilter(
  status: ScreeningStatus,
  filter: ScreeningStatusFilter,
): boolean {
  switch (filter) {
    case ScreeningStatusFilter.All:
      return true;
    case ScreeningStatusFilter.Recommended:
      return status === ScreeningStatus.Recommended;
    case ScreeningStatusFilter.Review:
      return status === ScreeningStatus.Review;
    case ScreeningStatusFilter.Rejected:
      return status === ScreeningStatus.Rejected;
  }
}
