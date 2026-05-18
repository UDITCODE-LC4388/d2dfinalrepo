import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { Logo } from "@/components/Logo";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { HealthTimeline } from "@/components/dashboard/HealthTimeline";
import { AIInsight } from "@/components/dashboard/AIInsight";
import { KnowledgeGraph } from "@/components/dashboard/KnowledgeGraph";
import { CommitExplorer } from "@/components/dashboard/CommitExplorer";
import { RiskSection } from "@/components/dashboard/RiskSection";
import { LoadingScreen } from "@/components/LoadingScreen";
import { analyzeRepo, type AnalyzeResponse } from "@/lib/api";

export const Route = createFileRoute("/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — Repo Health Intelligence" },
      { name: "description", content: "Live repository health, AI insights, and architectural risk dashboard." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const cached = sessionStorage.getItem("rhi:data");
    const url = sessionStorage.getItem("rhi:url") || "";
    setRepoUrl(url);
    if (cached) {
      try { setData(JSON.parse(cached)); } catch { /* ignore */ }
    } else {
      navigate({ to: "/" });
    }
  }, [navigate]);

  const handleReanalyze = async () => {
    if (!repoUrl) return;
    setLoading(true);
    setError(null);
    try {
      const fresh = await analyzeRepo(repoUrl);
      sessionStorage.setItem("rhi:data", JSON.stringify(fresh));
      setData(fresh);
    } catch {
      setError("Failed to refresh analysis");
    } finally {
      setLoading(false);
    }
  };

  if (!data) {
    return (
      <div className="min-h-screen grid place-items-center">
        <div className="h-10 w-10 rounded-full border-2 border-primary/30 border-t-primary animate-spin" />
      </div>
    );
  }

  return (
    <div className="relative min-h-screen">
      <div className="absolute inset-0 bg-hero opacity-50 pointer-events-none" />
      <div className="absolute inset-0 grid-bg pointer-events-none opacity-60" />

      <header className="relative z-10 px-6 lg:px-10 py-5 flex items-center justify-between border-b border-border/40 backdrop-blur-xl bg-white/40">
        <div className="flex items-center gap-6">
          <Logo />
          <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-secondary/60 text-xs">
            <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 text-muted-foreground" fill="currentColor"><path d="M12 .5C5.65.5.5 5.66.5 12.02c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.55v-2c-3.2.7-3.88-1.36-3.88-1.36-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.16-1.18 3.16-1.18.63 1.59.24 2.76.12 3.05.74.81 1.18 1.84 1.18 3.1 0 4.42-2.7 5.4-5.27 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.66.8.55A11.51 11.51 0 0 0 23.5 12C23.5 5.66 18.35.5 12 .5z" /></svg>
            <span className="font-medium text-foreground">{data.repo_name}</span>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleReanalyze}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl glass text-sm font-medium hover:shadow-elegant transition"
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5" /></svg>
            Re-analyze
          </button>
          <Link to="/" className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl gradient-primary text-white text-sm font-semibold shadow-glow">
            New repo
          </Link>
        </div>
      </header>

      <main className="relative z-10 px-6 lg:px-10 py-8 max-w-[1400px] mx-auto space-y-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <div className="text-xs uppercase tracking-[0.16em] text-muted-foreground font-medium">Repository</div>
          <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight gradient-text mt-1">{data.repo_name}</h1>
          {error && <p className="text-sm text-destructive mt-2">{error}</p>}
        </motion.div>

        {/* Metric cards */}
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <MetricCard
            index={0}
            label="Health Score"
            value={data.health_score}
            suffix="/100"
            tone="primary"
            delta="+2.4%"
            icon={<svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" /></svg>}
          />
          <MetricCard
            index={1}
            label="Risk Level"
            value={data.risk_level}
            tone={data.risk_level === "High" ? "danger" : data.risk_level === "Medium" ? "warning" : "success"}
            icon={<svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01" /></svg>}
          />
          <MetricCard
            index={2}
            label="Commits Analyzed"
            value={data.total_commits.toLocaleString()}
            tone="primary"
            icon={<svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="12" cy="12" r="4" /><path d="M1.05 12H7M17 12h5.95" /></svg>}
          />
          <MetricCard
            index={3}
            label="Bus Factor"
            value={data.bus_factor}
            tone={data.bus_factor < 3 ? "warning" : "success"}
            icon={<svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2"><circle cx="9" cy="7" r="4" /><path d="M3 21v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2M16 3.13a4 4 0 0 1 0 7.75M22 21v-2a4 4 0 0 0-3-3.87" /></svg>}
          />
          <MetricCard
            index={4}
            label="Architecture Stability"
            value={data.architecture_stability}
            suffix="%"
            tone="success"
            delta="stable"
            icon={<svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2"><path d="M3 3v18h18M7 14l4-4 4 4 6-6" /></svg>}
          />
        </div>

        {/* Chart + AI Insight */}
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <HealthTimeline data={data.health_timeline} />
          </div>
          <AIInsight insight={data.ai_insight} />
        </div>

        {/* Graph + Risks */}
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2">
            <KnowledgeGraph data={data.graph} />
          </div>
          <RiskSection risks={data.risks} />
        </div>

        {/* Commit explorer */}
        <CommitExplorer commits={data.commits} />

        <div className="text-center text-xs text-muted-foreground pt-4 pb-2">
          Repo Health Intelligence · powered by AI architectural analysis
        </div>
      </main>

      {loading && <LoadingScreen repo={repoUrl} />}
    </div>
  );
}
