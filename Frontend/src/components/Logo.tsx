import React from "react";

interface LogoProps {
  className?: string;
  showText?: boolean;
}

export function Logo({ className = "h-12 w-auto", showText = true }: LogoProps) {
  return (
    <svg viewBox="0 0 500 120" className={className} xmlns="http://www.w3.org/2000/svg">
      <g transform="translate(10, 10)">
        {/* Shield Outline */}
        <path
          d="M 10 15 Q 50 0 90 15 L 90 50 C 90 80 50 100 50 100 C 50 100 10 80 10 50 Z"
          fill="none"
          stroke="#1a365d"
          strokeWidth="8"
          strokeLinejoin="round"
        />

        {/* Compass Star */}
        <g transform="translate(50, 35) scale(0.8)">
          <path d="M 0 -25 L 5 -5 L 25 0 L 5 5 L 0 25 L -5 5 L -25 0 L -5 -5 Z" fill="#a18042" />
          <path d="M 0 -25 L 5 -5 L 0 0 Z" fill="#1a365d" />
          <path d="M 25 0 L 5 5 L 0 0 Z" fill="#1a365d" />
          <path d="M 0 25 L -5 5 L 0 0 Z" fill="#1a365d" />
          <path d="M -25 0 L -5 -5 L 0 0 Z" fill="#1a365d" />
        </g>

        {/* Road */}
        <path d="M 15 80 C 30 50 60 40 95 35 L 95 55 C 60 60 40 70 25 95 Z" fill="#4a5568" />
        {/* Dashed line on road */}
        <path d="M 22 85 C 35 60 60 50 90 45" fill="none" stroke="#ffffff" strokeWidth="2" strokeDasharray="6,4" />

        {/* Graph bars */}
        <g transform="translate(60, 65) scale(0.6)">
          <rect x="0" y="10" width="3" height="10" fill="#a18042" />
          <rect x="5" y="5" width="3" height="15" fill="#a18042" />
          <rect x="10" y="0" width="3" height="20" fill="#a18042" />
          <rect x="15" y="8" width="3" height="12" fill="#a18042" />
          <rect x="20" y="2" width="3" height="18" fill="#a18042" />
        </g>
      </g>

      {showText && (
        <>
          {/* Text */}
          <text x="120" y="65" fontFamily="Inter, sans-serif" fontSize="48" fontWeight="800" fill="#1a365d">
            Road<tspan fill="#4a5568">Sentinel</tspan>
          </text>
          <text
            x="125"
            y="90"
            fontFamily="Inter, sans-serif"
            fontSize="14"
            fontWeight="700"
            fill="#4a5568"
            letterSpacing="1.5"
          >
            ENTERPRISE FLEET INTELLIGENCE
          </text>
        </>
      )}
    </svg>
  );
}
