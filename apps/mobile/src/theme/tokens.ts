/**
 * AetherOS Mobile — Design Tokens
 *
 * Extracted from the web app's globals.css and enriched with
 * Vedic-astrology-inspired accents. These are the single source
 * of truth for every color, font size, spacing, and radius used
 * in the mobile UI.
 */

export const colors = {
  // ── Backgrounds ───────────────────────────────────────────────
  bg: {
    deep: '#050507',       // hsl(240, 10%, 2%)   — screen bg
    card: '#090a0e',       // hsl(240, 10%, 3.9%) — card surface
    elevated: '#1e1e22',   // hsl(240, 3.7%, 12%) — borders, inputs, raised elements
    glass: 'rgba(20, 20, 20, 0.55)',
    glassBorder: 'rgba(255, 255, 255, 0.04)',
  },

  // ── Foreground / Text ─────────────────────────────────────────
  fg: {
    primary: '#fafafa',    // hsl(0, 0%, 98%)
    secondary: '#c4c4cc',
    muted: '#a0a1ab',      // hsl(240, 5%, 65%)
    faint: '#5c5c6a',
  },

  // ── Accents (celestial palette) ───────────────────────────────
  accent: {
    indigo: '#6366f1',     // primary interactive / chart lines
    indigoMuted: 'rgba(99, 102, 241, 0.15)',
    amber: '#f59e0b',      // scores, yoga badges
    amberMuted: 'rgba(245, 158, 11, 0.15)',
    emerald: '#10b981',    // positive indicators
    emeraldMuted: 'rgba(16, 185, 129, 0.12)',
    rose: '#f43f5e',       // dosha / warnings
    roseMuted: 'rgba(244, 63, 94, 0.12)',
    violet: '#8b5cf6',     // dasha timeline
    violetMuted: 'rgba(139, 92, 246, 0.12)',
    sky: '#38bdf8',        // transit highlights
    skyMuted: 'rgba(56, 189, 248, 0.12)',
  },

  // ── Status / Semantic ─────────────────────────────────────────
  status: {
    success: '#10b981',
    warning: '#f59e0b',
    error: '#ef4444',
    info: '#6366f1',
  },

  // ── Chart-specific ────────────────────────────────────────────
  chart: {
    houseBorder: 'rgba(255, 255, 255, 0.08)',
    houseActive: 'rgba(99, 102, 241, 0.20)',
    planetGlow: 'rgba(245, 158, 11, 0.35)',
    gridLine: 'rgba(255, 255, 255, 0.04)',
  },
} as const;

export const fonts = {
  display: 'Outfit_700Bold',
  displayMedium: 'Outfit_500Medium',
  body: 'Inter_400Regular',
  bodyMedium: 'Inter_500Medium',
  bodySemibold: 'Inter_600SemiBold',
  mono: 'JetBrainsMono_400Regular',
} as const;

export const fontSizes = {
  xs: 11,
  sm: 13,
  base: 15,
  md: 17,
  lg: 20,
  xl: 24,
  '2xl': 30,
  '3xl': 36,
} as const;

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  '2xl': 24,
  '3xl': 32,
  '4xl': 40,
  '5xl': 48,
} as const;

export const radii = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  full: 9999,
} as const;

export const shadows = {
  card: {
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.4,
    shadowRadius: 24,
    elevation: 8,
  },
  glow: {
    shadowColor: colors.accent.indigo,
    shadowOffset: { width: 0, height: 0 },
    shadowOpacity: 0.3,
    shadowRadius: 16,
    elevation: 6,
  },
} as const;
