import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import {
  createJobDescription,
  getJobDescriptionForEdit,
  JobApiError,
  updateJobDescription,
  type JobDescriptionRequest,
} from "../../services/jobDescriptionApi";
import styles from "./CreateJobDescriptionPage.module.css";

/**
 * Creates a job, and edits one.
 *
 * The same form serves both: an edit is the create form with the posting
 * already in it. Splitting them would mean two copies of every field,
 * every validation rule and the live preview, which drift apart the first
 * time one of them gains a field.
 */
export default function CreateJobDescriptionPage() {
  const navigate = useNavigate();
  const { jobId } = useParams<{ jobId: string }>();

  const isEditing = Boolean(jobId);

  const [isLoading, setIsLoading] = useState(Boolean(jobId));
  const [loadError, setLoadError] = useState("");

  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] = useState("Full-time");
  const [jobSummary, setJobSummary] = useState("");

  const [requiredSkills, setRequiredSkills] = useState<string[]>([]);
  const [requiredSkillInput, setRequiredSkillInput] = useState("");

  const [preferredSkills, setPreferredSkills] = useState<string[]>([]);
  const [preferredSkillInput, setPreferredSkillInput] = useState("");

  const [responsibilities, setResponsibilities] = useState("");
  const [minimumYears, setMinimumYears] = useState("0");
  const [experienceLevel, setExperienceLevel] = useState("Entry-Level");

  const [education, setEducation] = useState("");
  const [certifications, setCertifications] = useState("");
  const [languages, setLanguages] = useState("");
  const [technicalStack, setTechnicalStack] = useState("");
  const [softSkills, setSoftSkills] = useState("");
  const [passingScore, setPassingScore] = useState("70");

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    if (!jobId) {
      return;
    }

    let cancelled = false;

    async function loadJob() {
      setIsLoading(true);
      setLoadError("");

      try {
        const job = await getJobDescriptionForEdit(jobId!);

        if (cancelled) {
          return;
        }

        setTitle(job.title);
        setDepartment(job.department);
        setLocation(job.location);
        setEmploymentType(job.employment_type);
        setJobSummary(job.job_summary);
        setRequiredSkills(job.required_skills);
        setPreferredSkills(job.preferred_skills);
        setResponsibilities(job.responsibilities.join("\n"));
        setMinimumYears(String(job.minimum_years));
        setExperienceLevel(job.experience_level);
        setEducation(job.education.join("\n"));
        setCertifications(job.certifications.join(", "));
        setLanguages(job.languages.join(", "));
        setTechnicalStack(job.technical_stack.join(", "));
        setSoftSkills(job.soft_skills.join(", "));
        setPassingScore(String(job.passing_score));
      } catch (error) {
        if (!cancelled) {
          setLoadError(
            error instanceof JobApiError
              ? error.message
              : "Failed to load this job. Please try again.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    loadJob();

    return () => {
      cancelled = true;
    };
  }, [jobId]);

  const addRequiredSkill = () => {
    const skill = requiredSkillInput.trim();

    if (
      skill &&
      !requiredSkills.some(
        (existingSkill) =>
          existingSkill.toLowerCase() === skill.toLowerCase(),
      )
    ) {
      setRequiredSkills([...requiredSkills, skill]);
    }

    setRequiredSkillInput("");
  };

  const addPreferredSkill = () => {
    const skill = preferredSkillInput.trim();

    if (
      skill &&
      !preferredSkills.some(
        (existingSkill) =>
          existingSkill.toLowerCase() === skill.toLowerCase(),
      )
    ) {
      setPreferredSkills([...preferredSkills, skill]);
    }

    setPreferredSkillInput("");
  };

  const removeRequiredSkill = (skillToRemove: string) => {
    setRequiredSkills(
      requiredSkills.filter((skill) => skill !== skillToRemove),
    );
  };

  const removePreferredSkill = (skillToRemove: string) => {
    setPreferredSkills(
      preferredSkills.filter((skill) => skill !== skillToRemove),
    );
  };

  const splitList = (value: string) =>
    value
      .split(/\n/)
      .map((item) => item.trim())
      .filter(Boolean);

  const splitCommaList = (value: string) =>
    value
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean);

  const handleCreateJob = async () => {
    setSuccessMessage("");
    setErrorMessage("");

    if (
      !title.trim() ||
      !department ||
      !location.trim() ||
      !jobSummary.trim()
    ) {
      setErrorMessage("Please complete all required fields.");
      return;
    }

    const parsedMinimumYears = Number(minimumYears);
    const parsedPassingScore =
      passingScore.trim() === "" ? 70 : Number(passingScore);

    if (
      minimumYears.trim() === "" ||
      Number.isNaN(parsedMinimumYears) ||
      parsedMinimumYears < 0
    ) {
      setErrorMessage("Minimum years of experience must be 0 or greater.");
      return;
    }

    if (
      Number.isNaN(parsedPassingScore) ||
      parsedPassingScore < 0 ||
      parsedPassingScore > 100
    ) {
      setErrorMessage("Passing score must be between 0 and 100.");
      return;
    }

    const finalRequiredSkills = [...requiredSkills];
    const pendingRequiredSkill = requiredSkillInput.trim();

    if (
      pendingRequiredSkill &&
      !finalRequiredSkills.some(
        (skill) => skill.toLowerCase() === pendingRequiredSkill.toLowerCase(),
      )
    ) {
      finalRequiredSkills.push(pendingRequiredSkill);
    }

    const finalPreferredSkills = [...preferredSkills];
    const pendingPreferredSkill = preferredSkillInput.trim();

    if (
      pendingPreferredSkill &&
      !finalPreferredSkills.some(
        (skill) => skill.toLowerCase() === pendingPreferredSkill.toLowerCase(),
      )
    ) {
      finalPreferredSkills.push(pendingPreferredSkill);
    }

    const request: JobDescriptionRequest = {
      role: {
        title: title.trim(),
        department,
        employment_type: employmentType,
        location: location.trim(),
      },
      job_summary: jobSummary.trim(),
      responsibilities: splitList(responsibilities),
      requirements: {
        skills: {
          required: finalRequiredSkills,
          preferred: finalPreferredSkills,
        },
        experience: {
          minimum_years: parsedMinimumYears,
          level: experienceLevel,
        },
        education: splitList(education),
        certifications: splitCommaList(certifications),
        languages: splitCommaList(languages),
      },
      technical_stack: splitCommaList(technicalStack),
      soft_skills: splitCommaList(softSkills),
      screening_settings: {
        passing_score: parsedPassingScore,
      },
    };

    try {
      setIsSubmitting(true);

      if (isEditing) {
        await updateJobDescription(jobId!, request);

        setSuccessMessage("Job updated successfully.");
      } else {
        // Temporary demo recruiter until authentication is integrated.
        await createJobDescription(1, request);

        setSuccessMessage("Job created successfully.");
      }
    } catch (error) {
      setErrorMessage(
        error instanceof JobApiError
          ? error.message
          : `Unable to ${isEditing ? "update" : "create"} the job. ` +
            "Please try again.",
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isLoading) {
    return (
      <main className={styles.page}>
        <Typography color="text.secondary">Loading job...</Typography>
      </main>
    );
  }

  if (loadError) {
    return (
      <main className={styles.page}>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate("/jobs")}
          sx={{ alignSelf: "flex-start", mb: 2 }}
        >
          Back to Jobs
        </Button>

        <Typography color="error.main">{loadError}</Typography>
      </main>
    );
  }

  return (
    <main className={styles.page}>
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate("/jobs")}
        sx={{ alignSelf: "flex-start", mb: 2 }}
      >
        Back to Jobs
      </Button>

      <Typography variant="h1" className={styles.title}>
        {isEditing ? "Edit job posting" : "New job posting"}
      </Typography>

      <Typography color="text.secondary" className={styles.subtitle}>
        {isEditing
          ? "Changes replace what candidates see. Editing the skills or " +
            "the passing score regenerates this job's screening criteria."
          : "Set the role details, requirements, and screening criteria " +
            "for this opportunity"}
      </Typography>

      <div className={styles.layout}>
        <Card className={styles.formCard}>
          <CardContent className={styles.cardContent}>
            <Typography variant="h2">Role details</Typography>

            <Typography color="text.secondary" className={styles.sectionText}>
              This is what candidates will see on the application page
            </Typography>

            <div className={styles.formGrid}>
              <TextField
                label="Job title"
                placeholder="e.g. Senior Backend Engineer"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                required
                fullWidth
              />

              <FormControl fullWidth required>
                <InputLabel>Department</InputLabel>
                <Select
                  label="Department"
                  value={department}
                  onChange={(event) => setDepartment(event.target.value)}
                >
                  <MenuItem value="Engineering">Engineering</MenuItem>
                  <MenuItem value="Product">Product</MenuItem>
                  <MenuItem value="Design">Design</MenuItem>
                  <MenuItem value="Human Resources">
                    Human Resources
                  </MenuItem>
                  <MenuItem value="Marketing">Marketing</MenuItem>
                  <MenuItem value="Sales">Sales</MenuItem>
                </Select>
              </FormControl>

              <TextField
                label="Location"
                placeholder="e.g. Remote"
                value={location}
                onChange={(event) => setLocation(event.target.value)}
                required
                fullWidth
              />

              <FormControl fullWidth required>
                <InputLabel>Employment type</InputLabel>
                <Select
                  label="Employment type"
                  value={employmentType}
                  onChange={(event) =>
                    setEmploymentType(event.target.value)
                  }
                >
                  <MenuItem value="Full-time">Full-time</MenuItem>
                  <MenuItem value="Part-time">Part-time</MenuItem>
                  <MenuItem value="Internship">Internship</MenuItem>
                  <MenuItem value="Contract">Contract</MenuItem>
                </Select>
              </FormControl>
            </div>

            <Typography className={styles.fieldLabel}>
              Required skills
            </Typography>

            <TextField
              fullWidth
              placeholder="Type a skill and press Enter"
              value={requiredSkillInput}
              onChange={(event) => setRequiredSkillInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  addRequiredSkill();
                }
              }}
            />

            {requiredSkills.length > 0 && (
              <Stack
                direction="row"
                spacing={1}
                useFlexGap
                flexWrap="wrap"
                className={styles.chips}
              >
                {requiredSkills.map((skill) => (
                  <Chip
                    key={skill}
                    label={skill}
                    onDelete={() => removeRequiredSkill(skill)}
                  />
                ))}
              </Stack>
            )}

            <Typography variant="body2" color="text.secondary">
              Required skills are used to guide candidate screening.
            </Typography>

            <Typography className={styles.fieldLabel}>
              Job description
            </Typography>

            <TextField
              fullWidth
              multiline
              minRows={5}
              placeholder="Describe the role, responsibilities, and what success looks like..."
              value={jobSummary}
              onChange={(event) => setJobSummary(event.target.value)}
              required
            />

            <Typography variant="h2" className={styles.sectionTitle}>
              Requirements
            </Typography>

            <Typography className={styles.fieldLabel}>
              Preferred skills
            </Typography>

            <TextField
              fullWidth
              placeholder="Type a preferred skill and press Enter"
              value={preferredSkillInput}
              onChange={(event) => setPreferredSkillInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  event.preventDefault();
                  addPreferredSkill();
                }
              }}
            />

            {preferredSkills.length > 0 && (
              <Stack
                direction="row"
                spacing={1}
                useFlexGap
                flexWrap="wrap"
                className={styles.chips}
              >
                {preferredSkills.map((skill) => (
                  <Chip
                    key={skill}
                    label={skill}
                    onDelete={() => removePreferredSkill(skill)}
                  />
                ))}
              </Stack>
            )}

            <div className={styles.formGrid}>
              <TextField
                label="Minimum years of experience"
                type="number"
                value={minimumYears}
                onChange={(event) => setMinimumYears(event.target.value)}
                slotProps={{
                  htmlInput: { min: 0 },
                }}
                fullWidth
              />

              <FormControl fullWidth required>
                <InputLabel>Experience level</InputLabel>
                <Select
                  label="Experience level"
                  value={experienceLevel}
                  onChange={(event) =>
                    setExperienceLevel(event.target.value)
                  }
                >
                  <MenuItem value="Entry-Level">Entry-Level</MenuItem>
                  <MenuItem value="Junior">Junior</MenuItem>
                  <MenuItem value="Mid-Level">Mid-Level</MenuItem>
                  <MenuItem value="Senior">Senior</MenuItem>
                  <MenuItem value="Lead">Lead</MenuItem>
                </Select>
              </FormControl>
            </div>

            <TextField
              label="Responsibilities"
              placeholder={
                "e.g. Build and maintain REST APIs\nWrite and review unit tests"
              }
              helperText="Enter one responsibility per line"
              value={responsibilities}
              onChange={(event) => setResponsibilities(event.target.value)}
              multiline
              minRows={3}
              fullWidth
            />

            <div className={styles.formGrid}>
              <TextField
                label="Education"
                placeholder="e.g. Bachelor's Degree"
                value={education}
                onChange={(event) => setEducation(event.target.value)}
                fullWidth
              />

              <TextField
                label="Certifications"
                placeholder="e.g. AWS, Azure"
                value={certifications}
                onChange={(event) => setCertifications(event.target.value)}
                fullWidth
              />
            </div>

            <div className={styles.formGrid}>
              <TextField
                label="Languages"
                placeholder="e.g. English, Arabic"
                value={languages}
                onChange={(event) => setLanguages(event.target.value)}
                fullWidth
              />

              <TextField
                label="Technical stack"
                placeholder="e.g. Python, FastAPI"
                value={technicalStack}
                onChange={(event) => setTechnicalStack(event.target.value)}
                fullWidth
              />
            </div>

            <TextField
              label="Soft skills"
              placeholder="e.g. Communication, Teamwork"
              value={softSkills}
              onChange={(event) => setSoftSkills(event.target.value)}
              fullWidth
            />

            <Typography variant="h2" className={styles.sectionTitle}>
              Screening settings
            </Typography>

            <Typography color="text.secondary" className={styles.sectionText}>
              Configure the minimum score required for a candidate to pass
              screening.
            </Typography>

            <TextField
              label="Passing score"
              type="number"
              value={passingScore}
              onChange={(event) => setPassingScore(event.target.value)}
              slotProps={{
                htmlInput: { min: 0, max: 100 },
              }}
              fullWidth
            />

            {successMessage && (
              <Typography color="success.main">
                {successMessage}
              </Typography>
            )}

            {errorMessage && (
              <Typography color="error.main">{errorMessage}</Typography>
            )}

            <Box className={styles.actions}>
            <Button
              variant="outlined"
              onClick={() => navigate(-1)}
              disabled={isSubmitting}
            >
              Cancel
            </Button>

            <Button
              variant="contained"
              onClick={handleCreateJob}
              disabled={isSubmitting || Boolean(successMessage)}
            >
              {isSubmitting
                ? isEditing
                  ? "Saving..."
                  : "Creating..."
                : successMessage
                  ? isEditing
                    ? "Changes saved"
                    : "Job created"
                  : isEditing
                    ? "Save changes"
                    : "Create job"}
            </Button>
            </Box>
          </CardContent>
        </Card>

        <aside className={styles.previewColumn}>
          <Typography className={styles.previewHeading}>
            Candidate view
          </Typography>

          <Card className={styles.previewCard}>
            <CardContent className={styles.previewContent}>
              <Typography className={styles.openRole}>
                Open role
              </Typography>

              <Typography variant="h1" className={styles.previewTitle}>
                {title || "Job title will appear here"}
              </Typography>

              <Typography color="text.secondary">
                {location || "Location"} · {employmentType}
              </Typography>

              <Typography
                color="text.secondary"
                className={styles.previewDescription}
              >
                {jobSummary ||
                  "Job description will appear here as you type."}
              </Typography>

              <Box className={styles.interviewCoverage}>
                <Typography fontWeight={650}>
                  What the interview covers
                </Typography>

                {requiredSkills.length > 0 ? (
                  <Stack
                    direction="row"
                    spacing={1}
                    useFlexGap
                    flexWrap="wrap"
                    className={styles.previewSkills}
                  >
                    {requiredSkills.map((skill) => (
                      <Chip key={skill} label={skill} />
                    ))}
                  </Stack>
                ) : (
                  <Typography color="text.secondary">
                    Add skill areas above
                  </Typography>
                )}
              </Box>
            </CardContent>
          </Card>
        </aside>
      </div>
    </main>
  );
}