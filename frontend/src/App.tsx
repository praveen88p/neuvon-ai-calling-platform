import * as Sentry from "@sentry/react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { DashboardLayout } from "@/components/DashboardLayout";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Dashboard from "./pages/Dashboard";
import Agents from "./pages/Agents";
import Campaigns from "./pages/Campaigns";
import CampaignDetails from "./pages/CampaignDetails";
import UploadLeads from "./pages/UploadLeads";
import LiveCalls from "./pages/LiveCalls";
import CallHistory from "./pages/CallHistory";
import CallDetails from "./pages/CallDetails";
import Analytics from "./pages/Analytics";
import Appointments from "./pages/Appointments";
import Settings from "./pages/Settings";
import PhoneNumbers from "./pages/PhoneNumbers";
import Logs from "./pages/admin/Logs";
import AuditTrail from "./pages/admin/AuditTrail";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,       // 1 min – data is "fresh" for 1 min after fetch
      gcTime: 5 * 60_000,      // 5 min – keep unused cache entries for 5 min
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

const SentryFallback = () => (
  <div className="flex items-center justify-center min-h-screen bg-background">
    <div className="text-center space-y-4 p-8">
      <h2 className="text-2xl font-bold text-foreground">Something went wrong</h2>
      <p className="text-muted-foreground">
        An unexpected error occurred. Our team has been notified.
      </p>
      <button
        onClick={() => window.location.reload()}
        className="inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
      >
        Reload Page
      </button>
    </div>
  </div>
);

const App = () => (
  <Sentry.ErrorBoundary fallback={SentryFallback}>
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <Routes>
              {/* Public routes */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />
              
              {/* Protected routes */}
              <Route
                path="/*"
                element={
                  <ProtectedRoute>
                    <DashboardLayout>
                      <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/agents" element={<Agents />} />
                        <Route path="/campaigns" element={<Campaigns />} />
                        <Route path="/campaigns/:id" element={<CampaignDetails />} />
                        <Route path="/upload" element={<UploadLeads />} />
                        <Route path="/live-calls" element={<LiveCalls />} />
                        <Route path="/call-history" element={<CallHistory />} />
                        <Route path="/call-details/:id" element={<CallDetails />} />
                        <Route path="/analytics" element={<Analytics />} />
                        <Route path="/appointments" element={<Appointments />} />
                        <Route path="/settings" element={<Settings />} />
                        <Route path="/phone-numbers" element={<PhoneNumbers />} />
                        <Route path="/admin/logs" element={<Logs />} />
                        <Route path="/admin/audit" element={<AuditTrail />} />
                        <Route path="*" element={<NotFound />} />
                      </Routes>
                    </DashboardLayout>
                  </ProtectedRoute>
                }
              />
            </Routes>
          </BrowserRouter>
        </TooltipProvider>
      </AuthProvider>
    </QueryClientProvider>
  </Sentry.ErrorBoundary>
);

export default App;
