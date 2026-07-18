import React from 'react';

// Origin's brand mark -- a stylized peepal (sacred fig) leaf: the broad,
// heart-ish blade tapering into the long drip-tip peepal leaves are known
// for. Drawn as a lucide-style outline icon (stroke only, currentColor) so
// it drops into the same slots the old flower mark used.
export default function PeepalLeaf({ className = '', strokeWidth = 1.5, ...props }) {
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
      <path d="M12 3C8 5 4 8 4 12.5C4 16 7 18.5 10.2 19.8C10.9 20.1 11.5 20.5 12 21C12.5 20.5 13.1 20.1 13.8 19.8C17 18.5 20 16 20 12.5C20 8 16 5 12 3Z" />
      <path d="M12 6.5V18" />
    </svg>
  );
}
