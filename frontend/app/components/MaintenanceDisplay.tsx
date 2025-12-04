"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
const POLL_INTERVAL = 30000; // Check every 30 seconds

export function MaintenanceDisplay() {
  const router = useRouter();
  const [dots, setDots] = useState("");

  useEffect(() => {
    // Animate dots
    const dotsInterval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 500);

    // Poll for maintenance status
    const pollStatus = async () => {
      try {
        const res = await fetch(`${API_BASE}/status`);
        if (res.ok) {
          const data = await res.json();
          if (!data.maintenance.is_running) {
            // Maintenance complete - refresh the page
            router.refresh();
          }
        }
      } catch {
        // Ignore errors, keep polling
      }
    };

    const pollInterval = setInterval(pollStatus, POLL_INTERVAL);

    return () => {
      clearInterval(dotsInterval);
      clearInterval(pollInterval);
    };
  }, [router]);

  return (
    <div className="flex flex-col items-center justify-center py-20 px-6">
      <div className="relative mb-8">
        <div className="w-20 h-20 border-4 border-gray-200 border-t-crimson rounded-full animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl">🔬</span>
        </div>
      </div>
      <h2 className="text-2xl font-bold text-gray-800 mb-3">
        Analysis in Progress{dots}
      </h2>
      <p className="text-gray-600 text-center max-w-md mb-4">
        We&apos;re fetching fresh articles and running our AI bias analysis.
        This typically takes a few minutes.
      </p>
      <p className="text-sm text-gray-500 animate-pulse">
        This page will refresh automatically when ready
      </p>
    </div>
  );
}



