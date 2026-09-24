import type { RefObject } from "react";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import { Box, Button, TextField, Typography } from "@mui/material";

import styles from "./CandidateApplicationPanel.module.css";

interface ApplicationFormProps {
  fullName: string;
  nameError: string;
  email: string;
  emailError: string;
  phone: string;
  phoneError: string;
  resumeFile: File | null;
  fileError: string;
  isPrechecking: boolean;
  isSubmitting: boolean;
  submitError: string;
  fileInputRef: RefObject<HTMLInputElement | null>;
  onFullNameChange: (value: string) => void;
  onEmailChange: (value: string) => void;
  onPhoneChange: (value: string) => void;
  onChooseFile: () => void;
  onFileSelected: (event: React.ChangeEvent<HTMLInputElement>) => void;
  onRemoveFile: () => void;
  onSubmit: () => void;
  onBack: () => void;
  formatFileSize: (bytes: number) => string;
}

/**
 * The candidate application form itself: name/email/phone/resume,
 * plus first-submission screening feedback (Task 3). The candidate
 * always types their own email here -- it is never pre-filled from a
 * previous visit or a previous candidate's submission on this
 * browser (see Task 4).
 */
export function ApplicationForm({
  fullName,
  nameError,
  email,
  emailError,
  phone,
  phoneError,
  resumeFile,
  fileError,
  isPrechecking,
  isSubmitting,
  submitError,
  fileInputRef,
  onFullNameChange,
  onEmailChange,
  onPhoneChange,
  onChooseFile,
  onFileSelected,
  onRemoveFile,
  onSubmit,
  onBack,
  formatFileSize,
}: ApplicationFormProps) {
  const isBusy = isPrechecking || isSubmitting;

  return (
    <>
      <Typography variant="h2" className={styles.title}>
        Apply for this Job
      </Typography>

      <div className={styles.formFields}>
        <TextField
          label="Full Name"
          value={fullName}
          onChange={(event) => onFullNameChange(event.target.value)}
          error={!!nameError}
          helperText={nameError || " "}
          disabled={isBusy}
          required
          fullWidth
        />

        <TextField
          label="Email"
          type="email"
          value={email}
          onChange={(event) => onEmailChange(event.target.value)}
          error={!!emailError}
          helperText={emailError || " "}
          disabled={isBusy}
          required
          fullWidth
        />

        <TextField
          label="Phone"
          value={phone}
          onChange={(event) => onPhoneChange(event.target.value)}
          error={!!phoneError}
          helperText={phoneError || " "}
          disabled={isBusy}
          required
          fullWidth
        />
      </div>

      <Typography className={styles.fieldLabel}>Resume *</Typography>

      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,application/pdf"
        onChange={onFileSelected}
        aria-label="Upload resume"
        hidden
      />

      <Box className={styles.uploadRow}>
        <Button
          variant="outlined"
          startIcon={<UploadFileIcon />}
          onClick={onChooseFile}
          disabled={isBusy}
        >
          Upload Resume
        </Button>
        <Typography color="text.secondary" className={styles.uploadHint}>
          PDF
        </Typography>
      </Box>

      {resumeFile && (
        <Box className={styles.selectedFile}>
          <Typography className={styles.selectedFileName}>
            {resumeFile.name}
            <span className={styles.selectedFileSize}>
              {" "}
              ({formatFileSize(resumeFile.size)})
            </span>
          </Typography>
          <Button
            variant="text"
            size="small"
            onClick={onRemoveFile}
            disabled={isBusy}
          >
            Remove
          </Button>
        </Box>
      )}

      {fileError && (
        <Typography color="error.main" className={styles.errorText}>
          {fileError}
        </Typography>
      )}

      {/* Task 3: while the (synchronous) submission request is
          screening this resume, say so explicitly near the Submit
          button rather than leaving the candidate looking at a bare
          "Submitting..." button with no idea what is happening. */}
      {isSubmitting && (
        <Typography className={styles.screeningMessage}>
          Your resume is currently in the screening phase.
          <br />
          Please wait until the screening process is finished.
        </Typography>
      )}

      {submitError && (
        <Typography color="error.main" className={styles.errorText}>
          {submitError}
        </Typography>
      )}

      <Box className={styles.actions}>
        <Button variant="text" onClick={onBack} disabled={isBusy}>
          Back
        </Button>
        <Button variant="contained" onClick={onSubmit} disabled={isBusy}>
          {isPrechecking
            ? "Checking..."
            : isSubmitting
              ? "Submitting..."
              : "Submit Application"}
        </Button>
      </Box>
    </>
  );
}
