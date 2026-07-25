import React from 'react';

// Origin's brand mark -- a minimal ox/bull head: two horns curving down to a
// rounded head with a muzzle line. Drawn lucide-style (stroke, currentColor)
// so it drops into the same slots the peepal leaf used.
export default function OxIcon({ className = '', strokeWidth = 1.7, ...props }) {
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
      <path d="M4.5 6C5.5 9.5 8 11 10.7 10.9" />
      <path d="M19.5 6C18.5 9.5 16 11 13.3 10.9" />
      <circle cx="12" cy="15" r="5.5" />
      <path d="M10 16.6h4" />
    </svg>
  );
}
