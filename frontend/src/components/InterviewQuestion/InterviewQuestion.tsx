import styles from './InterviewQuestion.module.css'

interface InterviewQuestionProps {
  question: string
  currentQuestion: number
  totalQuestions: number
  /** Marks a question the interview generated from the previous answer. */
  isFollowUp?: boolean
  /** Replaces the numeric progress label for conversational moments. */
  progressLabel?: string
}

function InterviewQuestion({
  question,
  currentQuestion,
  totalQuestions,
  isFollowUp = false,
  progressLabel,
}: InterviewQuestionProps) {
  return (
    <section className={styles.questionSection}>
      <p className={styles.progress}>
        {progressLabel ??
          (isFollowUp
          ? 'Follow-up to your last answer'
          : `Question ${currentQuestion} of ${totalQuestions}`)}
      </p>

      <h1 className={styles.question}>{question}</h1>
    </section>
  )
}

export default InterviewQuestion
