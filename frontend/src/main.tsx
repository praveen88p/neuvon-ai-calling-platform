import * as Sentry from "@sentry/react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// ── Sentry Initialization ──────────────────────────────────────────────────
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN;
if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.MODE, // "development" or "production"
    // Capture 20% of page loads for performance
    tracesSampleRate: 0.2,
    // Capture all frontend errors
    sampleRate: 1.0,
    // Capture console.error as breadcrumbs
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({ maskAllText: false, blockAllMedia: false }),
    ],
    // Capture 10% of sessions for replay (helps see what user did before crash)
    replaysSessionSampleRate: 0.1,
    // Capture 100% of sessions with errors for replay
    replaysOnErrorSampleRate: 1.0,
  });
}

createRoot(document.getElementById("root")!).render(<App />);
