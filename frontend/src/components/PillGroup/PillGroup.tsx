import Chip from "@mui/material/Chip";
import Typography from "@mui/material/Typography";
import { PillVariant } from "../../types/screeningTypes";
import styles from "./PillGroup.module.css";

interface PillGroupProps {
  label: string;
  values: string[];
  emptyText: string;
  variant: PillVariant;
}

export function PillGroup({
  label,
  values,
  emptyText,
  variant,
}: PillGroupProps) {
  const chipColor = variant === PillVariant.Matched ? "success" : "error";

  return (
    <div className={styles.group}>
      <Typography component="span" className={styles.label}>
        {label}
      </Typography>
      {values.length > 0 ? (
        <div className={styles.chips}>
          {values.map((value) => (
            <Chip
              key={value}
              label={value}
              color={chipColor}
              variant={variant === PillVariant.Matched ? "filled" : "outlined"}
              className={styles.chip}
            />
          ))}
        </div>
      ) : (
        <Typography component="p" className={styles.empty}>
          {emptyText}
        </Typography>
      )}
    </div>
  );
}
