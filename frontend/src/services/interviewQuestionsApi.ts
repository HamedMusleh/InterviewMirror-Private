export interface InterviewQuestionResponse {
  id: number
  interview_id: number
  question: string
  question_type: string
  skill: string | null
  sequence_number: number
  is_follow_up: boolean
  parent_question_id: number | null
}

export interface InterviewStatusResponse {
  interview_id: number
  status: string
  completed: boolean
  next_question: InterviewQuestionResponse | null

  /*
   * How many questions already have a stored answer. Used only to word the
   * resume prompt; whether to resume at all is decided by started_at.
   */
  answered_count: number

  /*
   * When the candidate first opened the room, or null if they never have.
   *
   * A non-null value means this interview is being resumed rather than
   * begun, which is what the room uses to drop the candidate back on the
   * question they were on instead of replaying the greeting and check-in.
   * The answer count cannot stand in for it: a candidate who reloads while
   * still on the first question has answered nothing but has already been
   * greeted.
   */
  started_at: string | null

  /*
   * How long the interview has been running, measured on the server so a
   * skewed device clock cannot produce a wrong or negative timer.
   */
  elapsed_seconds: number
}

/*
 * The status payload as it comes off the wire.
 *
 * Every field added after the first release is optional here, so a frontend
 * deployed ahead of its backend reads an interview that has not started with
 * no answers, and degrades to beginning from the top rather than breaking.
 */
interface InterviewStatusApiResponse {
  interview_id: number
  status: string
  completed: boolean
  answered_count?: number
  started_at?: string | null
  elapsed_seconds?: number
  next_question?: {
    id: number
    interview_id: number
    question_text: string
    question_type: string
    skill: string | null
    sequence_number: number
    is_follow_up: boolean
    parent_question_id: number | null
  } | null
}

interface InterviewQuestionsApiResponse {
  questions: {
    id: number
    interview_id: number
    question_text: string
    question_type: string
    skill: string | null
    sequence_number: number
    is_follow_up: boolean
    parent_question_id: number | null
  }[]
}

const API_BASE_URL =
  `${import.meta.env.VITE_API_BASE_URL}/api/interview-questions`

const INTERVIEW_FLOW_API_BASE_URL =
  `${import.meta.env.VITE_API_BASE_URL}/api/interview-flow`


export async function getInterviewQuestions(
  interviewId: string,
): Promise<InterviewQuestionResponse[]> {
  const response = await fetch(
    `${API_BASE_URL}/${encodeURIComponent(interviewId)}`,
  )

  if (!response.ok) {
    throw new Error('Failed to fetch interview questions')
  }

  const data: InterviewQuestionsApiResponse =
    await response.json()

  return data.questions.map((item) => ({
    id: item.id,
    interview_id: item.interview_id,
    question: item.question_text,
    question_type: item.question_type,
    skill: item.skill,
    sequence_number: item.sequence_number,
    is_follow_up: item.is_follow_up,
    parent_question_id: item.parent_question_id,
  }))
}


/**
 * Mark the interview as begun and read back where the candidate is.
 *
 * Called every time the room opens, a reload included. The start stamp is
 * written only on the first call, so the elapsed clock counts from the real
 * beginning of the interview rather than restarting on every page load.
 */
export async function startInterview(
  interviewId: string,
): Promise<InterviewStatusResponse> {
  const response = await fetch(
    `${INTERVIEW_FLOW_API_BASE_URL}/${encodeURIComponent(interviewId)}/start`,
    {
      method: 'POST',
    },
  )

  if (!response.ok) {
    throw new Error('Failed to start the interview')
  }

  return toInterviewStatus(await response.json())
}


export async function getInterviewStatus(
  interviewId: string,
): Promise<InterviewStatusResponse> {
  const response = await fetch(
    `${INTERVIEW_FLOW_API_BASE_URL}/${encodeURIComponent(interviewId)}/status`,
  )

  if (!response.ok) {
    throw new Error('Failed to load interview status')
  }

  return toInterviewStatus(await response.json())
}


/*
 * Shared by both status calls.
 *
 * Every field is defaulted, so a backend that predates them reports an
 * interview that has not started with no answers -- which degrades to the
 * old always-begin-from-the-top behaviour rather than breaking the room.
 */
function toInterviewStatus(
  data: InterviewStatusApiResponse,
): InterviewStatusResponse {
  return {
    interview_id: data.interview_id,
    status: data.status,
    completed: data.completed,
    answered_count: data.answered_count ?? 0,
    started_at: data.started_at ?? null,
    elapsed_seconds: data.elapsed_seconds ?? 0,
    next_question: data.next_question
      ? {
          id: data.next_question.id,
          interview_id: data.next_question.interview_id,
          question: data.next_question.question_text,
          question_type:
            data.next_question.question_type,
          skill: data.next_question.skill,
          sequence_number:
            data.next_question.sequence_number,
          is_follow_up:
            data.next_question.is_follow_up,
          parent_question_id:
            data.next_question.parent_question_id,
        }
      : null,
  }
}