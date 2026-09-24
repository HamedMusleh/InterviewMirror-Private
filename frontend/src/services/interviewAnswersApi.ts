export interface InterviewAnswerResponse {
  id: number
  question_id: number
  answer_text: string | null
  audio_url: string | null
  video_url: string | null
  transcript: string | null
  answered_at: string
}

const API_BASE_URL = `${import.meta.env.VITE_API_BASE_URL}/api/interview-answers`

export async function uploadInterviewAnswer(
  questionId: number,
  audio: Blob,
): Promise<InterviewAnswerResponse> {
  const formData = new FormData()

  formData.append('question_id', String(questionId))
  formData.append('audio', audio, `answer-${questionId}.webm`)

  const response = await fetch(`${API_BASE_URL}/audio`, {
    method: 'POST',
    body: formData,
  })

  if (!response.ok) {
    throw new Error('Failed to upload interview answer')
  }

  return response.json()
}