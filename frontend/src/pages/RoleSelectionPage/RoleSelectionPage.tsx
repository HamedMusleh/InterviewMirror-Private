import styles from "./RoleSelectionPage.module.css";

type Role = "candidate" | "recruiter";

interface RoleSelectionPageProps {
  onSelectRole: (role: Role) => void;
}

export default function RoleSelectionPage({
  onSelectRole,
}: RoleSelectionPageProps) {
  return (
    <main className={styles.page}>
      <section className={styles.container}>
        <div className={styles.brand}>InterviewMirror</div>

        <div className={styles.heading}>
          <h1>Welcome to InterviewMirror</h1>
          <p>Choose how you would like to continue.</p>
        </div>

        <div className={styles.roles}>
          <button
            type="button"
            className={styles.roleCard}
            onClick={() => onSelectRole("candidate")}
          >
            <div className={styles.icon}>C</div>

            <h2>Candidate</h2>

            <span className={styles.continueText}>
              Continue as Candidate →
            </span>
          </button>

          <button
            type="button"
            className={styles.roleCard}
            onClick={() => onSelectRole("recruiter")}
          >
            <div className={styles.icon}>R</div>

            <h2>Recruiter</h2>

            <span className={styles.continueText}>
              Continue as Recruiter →
            </span>
          </button>
        </div>
      </section>
    </main>
  );
}