import Chip from "@mui/material/Chip";
import { SCREENING_STATUS_LABELS } from "./const";
import type { ScreeningStatus } from "../../types/screeningTypes";
import { muiColorForStatus } from "../../utils/screeningUtils";
import styles from "./StatusBadge.module.css";

interface StatusBadgeProps {
  status: ScreeningStatus;
  className?: string;
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  const chipClassName = [styles.badge, className].filter(Boolean).join(" ");

  return (
    <Chip
      className={chipClassName}
      label={SCREENING_STATUS_LABELS[status]}
      color={muiColorForStatus(status)}
      variant="outlined"
    />
  );
}
