import { createTheme } from "@mui/material/styles";

export const appTheme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#2b3a67",
    },
    success: {
      main: "#178a6d",
      light: "#e4f5ef",
      dark: "#0f654f",
    },
    warning: {
      main: "#b3760a",
      light: "#fbf0dc",
      dark: "#7b5006",
    },
    error: {
      main: "#b8402a",
      light: "#fbe9e4",
      dark: "#842d1e",
    },
    background: {
      default: "#f7f8fa",
      paper: "#ffffff",
    },
    text: {
      primary: "#1b2440",
      secondary: "#565d6d",
    },
    divider: "#e4e7ed",
  },
  shape: {
    borderRadius: 10,
  },
  typography: {
    fontFamily: 'Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
    h1: {
      fontSize: "1.875rem",
      fontWeight: 650,
      lineHeight: 1.2,
    },
    h2: {
      fontSize: "1.125rem",
      fontWeight: 650,
      lineHeight: 1.3,
    },
    button: {
      textTransform: "none",
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      defaultProps: {
        disableElevation: true,
      },
    },
    MuiCard: {
      defaultProps: {
        variant: "outlined",
      },
    },
    MuiChip: {
      defaultProps: {
        size: "small",
      },
    },
  },
});
