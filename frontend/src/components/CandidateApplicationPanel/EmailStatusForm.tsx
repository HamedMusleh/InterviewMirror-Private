import { Box, Button, TextField, Typography } from "@mui/material";

import styles from "./CandidateApplicationPanel.module.css";

interface EmailStatusFormProps {
  title: string;
  email: string;
  emailError: string;
  isSubmitting: boolean;
  submitError: string;
  submitLabel: string;
  onEmailChange: (value: string) => void;
  onSubmit: () => void;
  onBack: () => void;
}

/**
 * A single explicit email input used to look up an existing
 * application's status. There is no default value and nothing is
 * pre-filled from browser storage -- the candidate always types the
 * email themselves (see Task 4/5).
 */
export function EmailStatusForm({
  title,
  email,
  emailError,
  isSubmitting,
  submitError,
  submitLabel,
  onEmailChange,
  onSubmit,
  onBack,
}: EmailStatusFormProps) {
  return (
    <>
      <Typography variant="h2" className={styles.title}>
        {title}
      </Typography>

      <div className={styles.formFields}>
        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(event) => onEmailChange(event.target.value)}
          error={!!emailError}
          helperText={emailError || " "}
          disabled={isSubmitting}
          required
          fullWidth
        />
      </div>

      {submitError && (
        <Typography color="error.main" className={styles.errorText}>
          {submitError}
        </Typography>
      )}

      <Box className={styles.actions}>
        <Button variant="text" onClick={onBack} disabled={isSubmitting}>
          Back
        </Button>
        <Button
          variant="contained"
          onClick={onSubmit}
          disabled={isSubmitting}
        >
          {isSubmitting ? "Checking..." : submitLabel}
        </Button>
      </Box>
    </>
  );
}
