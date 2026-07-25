import React from 'react';

// The Management app's brand mark -- a river: three flowing water lines.
// Drawn lucide-style (stroke, currentColor).
export default function RiverIcon({ className = '', strokeWidth = 1.8, ...props }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      {...props}
    >
      <path d="M2 7q3 -3 6 0 t6 0 t6 0" />
      <path d="M2 12q3 -3 6 0 t6 0 t6 0" />
      <path d="M2 17q3 -3 6 0 t6 0 t6 0" />
    </svg>
  );
}
