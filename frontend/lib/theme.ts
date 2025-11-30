/**
 * Centralized Theme Configuration for Veritas News
 * Harvard-inspired color scheme with white background and crimson accents
 */

// =============================================================================
// COLOR PALETTE
// =============================================================================

export const colors = {
  // Primary Harvard colors
  crimson: "#a51c30",
  crimsonDark: "#8a1726",
  crimsonLight: "#c73a4e",
  black: "#1e1e1e",
  white: "#ffffff",

  // Bias indicator colors
  left: {
    primary: "#2563eb", // blue-600
    light: "#dbeafe", // blue-100
    border: "#60a5fa", // blue-400
  },
  center: {
    primary: "#a51c30", // crimson
    light: "#fef2f2", // red-50
    border: "#a51c30",
  },
  right: {
    primary: "#dc2626", // red-600
    light: "#fee2e2", // red-100
    border: "#f87171", // red-400
  },
  unknown: {
    primary: "#6b7280", // gray-500
    light: "#f9fafb", // gray-50
    border: "#d1d5db", // gray-300
  },

  // Neutral colors
  gray: {
    50: "#f9fafb",
    100: "#f3f4f6",
    200: "#e5e7eb",
    300: "#d1d5db",
    400: "#9ca3af",
    500: "#6b7280",
    600: "#4b5563",
    700: "#374151",
  },
} as const;

// =============================================================================
// TAILWIND CLASS COMPOSITIONS
// =============================================================================

/** Common layout classes */
export const layout = {
  container: "mx-auto max-w-7xl px-4 sm:px-6 lg:px-8",
  containerNarrow: "mx-auto max-w-4xl px-4 sm:px-6 lg:px-8",
  section: "py-8",
} as const;

/** Typography classes */
export const typography = {
  h1: "text-3xl font-bold tracking-tight text-foreground sm:text-4xl",
  h2: "text-lg font-semibold text-foreground",
  h3: "text-base font-semibold text-foreground",
  body: "text-gray-600",
  bodySmall: "text-sm text-gray-600",
  caption: "text-xs text-gray-500",
  accent: "text-crimson",
} as const;

/** Card styles */
export const card = {
  base: "rounded-lg border-2 bg-white shadow-sm",
  hover: "transition-all duration-200 hover:shadow-lg hover:scale-[1.02] hover:border-crimson",
  padding: "p-4",
  paddingLarge: "p-6",
} as const;

/** Button styles */
export const button = {
  primary: "inline-flex items-center gap-2 rounded-lg bg-crimson px-6 py-3 font-medium text-white transition-colors hover:bg-crimson-dark",
  secondary: "inline-flex items-center gap-2 rounded-lg border-2 border-crimson px-6 py-3 font-medium text-crimson transition-colors hover:bg-crimson hover:text-white",
  link: "text-sm font-medium text-gray-600 transition-colors hover:text-crimson",
} as const;

/** Badge styles */
export const badge = {
  base: "shrink-0 rounded-full px-3 py-1 text-xs font-bold uppercase tracking-wide",
} as const;

// =============================================================================
// POLITICAL LEANING STYLES
// =============================================================================

import type { PoliticalLeaning } from "./api/types";

export interface LeaningStyle {
  border: string;
  badge: string;
  barColor: string;
  columnHeader: string;
}

export function getLeaningTheme(leaning: PoliticalLeaning): LeaningStyle {
  switch (leaning) {
    case "left":
      return {
        border: "border-blue-400",
        badge: "bg-blue-600 text-white",
        barColor: "bg-blue-600",
        columnHeader: "bg-blue-600 text-white",
      };
    case "center":
      return {
        border: "border-crimson",
        badge: "bg-crimson text-white",
        barColor: "bg-crimson",
        columnHeader: "bg-crimson text-white",
      };
    case "right":
      return {
        border: "border-red-400",
        badge: "bg-red-600 text-white",
        barColor: "bg-red-600",
        columnHeader: "bg-red-600 text-white",
      };
    case "unknown":
      return {
        border: "border-gray-300",
        badge: "bg-gray-500 text-white",
        barColor: "bg-gray-400",
        columnHeader: "bg-gray-600 text-white",
      };
  }
}

// =============================================================================
// COMPONENT-SPECIFIC STYLES
// =============================================================================

/** Header component styles */
export const header = {
  wrapper: "sticky top-0 z-50 w-full border-b-2 border-crimson bg-white shadow-sm",
  container: "mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8",
  logo: "text-2xl font-bold tracking-tight",
  logoAccent: "text-crimson",
  logoText: "text-foreground",
  nav: "flex items-center gap-6",
  navLink: "text-sm font-medium text-gray-600 transition-colors hover:text-crimson",
  navBadge: "text-xs text-crimson font-medium",
} as const;

/** Footer component styles */
export const footer = {
  wrapper: "border-t-2 border-crimson bg-white py-6",
  container: "mx-auto max-w-7xl px-4 text-center text-sm text-foreground sm:px-6 lg:px-8",
  text: "font-medium",
  subtext: "mt-1 text-xs text-gray-500",
} as const;

/** Article card styles */
export const articleCard = {
  wrapper: "block",
  article: "rounded-lg border-2 p-4 bg-white transition-all duration-200 hover:shadow-lg hover:scale-[1.02] hover:border-crimson",
  titleRow: "mb-2 flex items-start justify-between gap-2",
  title: "line-clamp-2 text-base font-semibold text-foreground",
  meta: "mt-3 flex flex-wrap items-center gap-3 text-xs text-gray-600",
  metaIcon: "h-3 w-3 text-crimson",
  biasSection: "mt-3 pt-3 border-t border-gray-200",
  biasLabel: "text-xs font-semibold text-foreground",
  biasScore: "text-xs font-bold text-crimson",
  biasBar: "h-2 flex-1 overflow-hidden rounded-full bg-gray-200",
} as const;

/** Column styles for article groups */
export const column = {
  wrapper: "flex flex-col rounded-lg border-2 bg-white shadow-sm",
  header: "rounded-t-lg px-4 py-3",
  headerTitle: "text-lg font-semibold",
  headerCount: "text-sm opacity-90",
  content: "flex flex-1 flex-col gap-3 p-4 bg-gray-50",
  empty: "py-8 text-center text-sm text-gray-500",
} as const;

/** Skeleton/loading styles */
export const skeleton = {
  base: "animate-pulse rounded bg-gray-300",
  light: "animate-pulse rounded bg-gray-200",
  pill: "animate-pulse rounded-full bg-gray-300",
} as const;

/** Legend component styles */
export const legend = {
  wrapper: "mb-6 flex flex-wrap items-center justify-center gap-6 text-sm bg-gray-50 rounded-lg py-4 px-6 border border-gray-200",
  label: "font-semibold text-foreground",
  item: "flex items-center gap-2",
  dot: "h-3 w-3 rounded-full",
  text: "text-gray-700",
} as const;

/** Error state styles */
export const error = {
  wrapper: "rounded-lg border-2 border-red-300 bg-red-50 p-6 text-center",
  title: "text-lg font-semibold text-red-700",
  message: "mt-2 text-sm text-red-600",
  hint: "mt-4 text-sm text-gray-600",
  code: "rounded bg-gray-100 px-1 py-0.5 text-xs",
} as const;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/** Combine multiple class strings */
export function cn(...classes: (string | undefined | false)[]): string {
  return classes.filter(Boolean).join(" ");
}
