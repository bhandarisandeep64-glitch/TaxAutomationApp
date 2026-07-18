// Corporate design system, for "Origin" (by BG Corp Global).
// A deep, precise indigo drives every interactive element across the whole
// app -- buttons, active nav, focus rings, highlighted totals. Flat panels
// with crisp 1px borders, not glassmorphism/glow, read as institutional
// software rather than a consumer app. A muted peepal-leaf green is
// reserved for the brand mark only (logo, login) so identity persists
// without competing with the functional accent.

export const THEME = {
  // Backgrounds
  bg: "bg-neutral-950",
  bgSubtle: "bg-neutral-900",
  card: "bg-neutral-900 border border-white/[0.07]",
  cardSolid: "bg-neutral-900 border border-white/[0.07]",
  surfaceElevated: "bg-neutral-800/50 border border-white/[0.08]",
  surfaceSunken: "bg-black/40 border border-white/[0.06]",

  sidebar: "bg-neutral-950 border-r border-white/[0.07]",

  // Text
  textMain: "text-neutral-100",
  textSecondary: "text-neutral-400",
  textMuted: "text-neutral-500",
  textHighlight: "text-indigo-400",

  // Borders
  border: "border-white/[0.07]",
  borderHover: "hover:border-white/[0.14]",
  borderAccent: "border-indigo-500/30",

  // Brand mark only -- logo, login screen. Never used for buttons/nav/status.
  brand: "text-green-800",
  brandSoft: "text-green-900/70",
  brandGlow: "shadow-[0_0_24px_rgba(20,83,45,0.25)]",

  // Accent -- the one interactive signal used everywhere (buttons, active
  // nav, focus rings, highlighted totals)
  accent: "text-indigo-400",
  accentBg: "bg-indigo-600",
  accentBorder: "border-indigo-500/40",
  accentHover: "hover:bg-indigo-500",
  accentSoft: "bg-indigo-500/10",
  accentRing: "focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/60",

  // Status colors (tables, badges, results)
  success: "text-emerald-400",
  successBg: "bg-emerald-500/10 border-emerald-500/30",
  error: "text-red-400",
  errorBg: "bg-red-500/10 border-red-500/30",
  warning: "text-amber-400",
  warningBg: "bg-amber-500/10 border-amber-500/30",
  info: "text-sky-400",
  infoBg: "bg-sky-500/10 border-sky-500/30",
  neutralBg: "bg-neutral-700/20 border-neutral-700/40",

  // Buttons
  buttonPrimary: "bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-sm transition-colors disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:bg-indigo-600",
  buttonSecondary: "bg-neutral-800 hover:bg-neutral-700 text-neutral-200 border border-white/[0.08] transition-colors",
  buttonGhost: "hover:bg-white/[0.04] text-neutral-400 hover:text-neutral-100 transition-colors",
  buttonDanger: "bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 transition-colors",

  // Inputs
  input: "bg-black/30 border border-white/[0.08] text-neutral-100 placeholder-neutral-600 focus:outline-none focus:border-indigo-500/60 focus:ring-2 focus:ring-indigo-500/20 transition-colors",
};
