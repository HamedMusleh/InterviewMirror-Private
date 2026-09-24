import MenuIcon from "@mui/icons-material/Menu";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { useState } from "react";
import { Link as RouterLink, useLocation } from "react-router";
import type { Role } from "../../types/roleTypes";

interface NavItem {
  label: string;
  to: string;
  /** Roles allowed to see this destination. */
  roles: Role[];
  /**
   * Whether the current URL belongs to this destination.
   *
   * Not a prefix match on `to`: a candidate's screening results live under
   * /jobs/:jobId/screening-results, which belongs to Screening Results
   * rather than to Home even though the path starts with /jobs.
   */
  matches: (pathname: string) => boolean;
}

const JOB_SCREENING_RESULTS = /^\/jobs\/[^/]+\/screening-results/;

// Matches /jobs/:jobId (the Job Details page) but not
// /jobs/:jobId/screening-results, which the Screening Results item
// below owns instead.
const JOB_DETAILS = /^\/jobs\/[^/]+\/?$/;

const NAV_ITEMS: NavItem[] = [
  {
    label: "Home",
    to: "/jobs",
    roles: ["candidate", "recruiter"],
    matches: (pathname) =>
      pathname === "/jobs" ||
      pathname.startsWith("/jobs/new") ||
      JOB_DETAILS.test(pathname),
  },
  {
    label: "Screening Results",
    to: "/screening-results",
    roles: ["recruiter"],
    matches: (pathname) =>
      pathname.startsWith("/screening-results") ||
      JOB_SCREENING_RESULTS.test(pathname),
  },
  {
    label: "Reports",
    to: "/reports",
    roles: ["recruiter"],
    matches: (pathname) =>
      pathname.startsWith("/reports") ||
      pathname.startsWith("/candidate-report"),
  },
];

/**
 * Routes that own the whole screen.
 *
 * The role selection screen is the gate before a role exists, so there is
 * nothing to navigate yet. The interview room is a live recorded session
 * where a stray click costs the candidate their answer.
 */
function isChromeless(pathname: string): boolean {
  return pathname === "/" || pathname.startsWith("/interview/");
}

function visibleItems(role: Role | null): NavItem[] {
  if (role === null) {
    return [];
  }

  return NAV_ITEMS.filter((item) => item.roles.includes(role));
}

interface NavBarProps {
  role: Role | null;
  onChangeRole: () => void;
}

export default function NavBar({ role, onChangeRole }: NavBarProps) {
  const { pathname } = useLocation();
  const [menuAnchor, setMenuAnchor] = useState<HTMLElement | null>(null);

  if (isChromeless(pathname)) {
    return null;
  }

  const items = visibleItems(role);
  const closeMenu = () => setMenuAnchor(null);

  return (
    <AppBar
      position="sticky"
      elevation={0}
      color="inherit"
      sx={{
        backgroundColor: "background.paper",
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <Toolbar
        component="nav"
        aria-label="Main"
        sx={{ gap: { xs: 1, md: 2 }, px: { xs: 2, md: 3 } }}
      >
        <Typography
          component={RouterLink}
          to={role ? "/jobs" : "/"}
          sx={{
            mr: { md: 1 },
            fontSize: "1rem",
            fontWeight: 700,
            letterSpacing: "-0.01em",
            color: "text.primary",
            textDecoration: "none",
            whiteSpace: "nowrap",
            "&:hover": { color: "primary.main" },
            "&:focus-visible": {
              outline: "2px solid",
              outlineColor: "primary.main",
              outlineOffset: 4,
              borderRadius: 1,
            },
          }}
        >
          InterviewMirror
        </Typography>

        {/* Wide viewports: the destinations sit inline. */}
        <Box
          sx={{
            display: { xs: "none", md: "flex" },
            alignItems: "center",
            gap: 0.5,
          }}
        >
          {items.map((item) => {
            const active = item.matches(pathname);

            return (
              <Button
                key={item.to}
                component={RouterLink}
                to={item.to}
                aria-current={active ? "page" : undefined}
                disableRipple
                sx={{
                  position: "relative",
                  px: 1.5,
                  py: 1,
                  fontSize: "0.875rem",
                  fontWeight: active ? 650 : 500,
                  color: active ? "primary.main" : "text.secondary",
                  transition: "color 160ms ease-out",
                  "&:hover": {
                    backgroundColor: "action.hover",
                    color: "text.primary",
                  },
                  "&:focus-visible": {
                    outline: "2px solid",
                    outlineColor: "primary.main",
                    outlineOffset: 2,
                  },
                  // The current-page marker. Sits on the toolbar's bottom
                  // border so the active tab reads as joined to the page.
                  "&::after": {
                    content: '""',
                    position: "absolute",
                    left: 12,
                    right: 12,
                    bottom: -1,
                    height: 2,
                    borderRadius: 1,
                    backgroundColor: "primary.main",
                    opacity: active ? 1 : 0,
                    transition: "opacity 160ms ease-out",
                  },
                  "@media (prefers-reduced-motion: reduce)": {
                    transition: "none",
                    "&::after": { transition: "none" },
                  },
                }}
              >
                {item.label}
              </Button>
            );
          })}
        </Box>

        <Box sx={{ flexGrow: 1 }} />

        {role ? (
          <Chip
            label={role === "recruiter" ? "Recruiter" : "Candidate"}
            size="small"
            onClick={onChangeRole}
            aria-label={`Signed in as ${role}. Change role`}
            sx={{
              fontWeight: 600,
              backgroundColor: "action.hover",
              color: "text.primary",
              "&:focus-visible": {
                outline: "2px solid",
                outlineColor: "primary.main",
                outlineOffset: 2,
              },
            }}
          />
        ) : (
          <Button
            component={RouterLink}
            to="/"
            size="small"
            variant="outlined"
            sx={{ fontSize: "0.8125rem" }}
          >
            Choose role
          </Button>
        )}

        {/* Narrow viewports: the same destinations, collapsed. */}
        {items.length > 0 && (
          <Box sx={{ display: { xs: "flex", md: "none" } }}>
            <IconButton
              edge="end"
              aria-label="Open navigation menu"
              aria-haspopup="menu"
              aria-expanded={menuAnchor !== null}
              onClick={(event) => setMenuAnchor(event.currentTarget)}
            >
              <MenuIcon />
            </IconButton>

            <Menu
              anchorEl={menuAnchor}
              open={menuAnchor !== null}
              onClose={closeMenu}
              anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
              transformOrigin={{ vertical: "top", horizontal: "right" }}
            >
              {items.map((item) => {
                const active = item.matches(pathname);

                return (
                  <MenuItem
                    key={item.to}
                    component={RouterLink}
                    to={item.to}
                    selected={active}
                    aria-current={active ? "page" : undefined}
                    onClick={closeMenu}
                    sx={{
                      fontSize: "0.875rem",
                      fontWeight: active ? 650 : 500,
                      color: active ? "primary.main" : "text.primary",
                    }}
                  >
                    {item.label}
                  </MenuItem>
                );
              })}
            </Menu>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
}
