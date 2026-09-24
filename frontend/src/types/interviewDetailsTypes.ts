export interface InterviewQuestionDetail {
  question_id: number;
  question: string;
  skill: string | null;
  is_follow_up: boolean;
  parent_question_id: number | null;
  answer: string | null;
  score: number | null;
  relevance_score: number | null;
  correctness_score: number | null;
  depth_score: number | null;
  practicality_score: number | null;
  strengths: string[];
  weaknesses: string[];
}

export interface InterviewDetailsResponse {
  interview_id: number;
  questions: InterviewQuestionDetail[];
}

export type InterviewDetailsViewState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "success"; data: InterviewDetailsResponse };