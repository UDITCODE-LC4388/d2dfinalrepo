import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { motion, AnimatePresence } from "framer-motion";
import { useEffect, useState } from "react";
import { 
  LayoutDashboard, FolderGit, GitCommit, ShieldAlert, BarChart3,
  RotateCw, ArrowLeft, RefreshCw 
} from "lucide-react";
import { Logo } from "@/components/Logo";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { HealthTimeline } from "@/components/dashboard/HealthTimeline";
import { AIInsight } from "@/components/dashboard/AIInsight";
import { FileGraphTree } from "@/components/dashboard/FileGraphTree";
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

type TabId = "overview" | "file-tree" | "commits" | "quality" | "risks";

function getLanguageColor(lang: string): string {
  const colors: Record<string, string> = {
    Python: "#3572A5",
    TypeScript: "#3178C6",
    TSX: "#2F74C0",
    JavaScript: "#F1E05A",
    JSX: "#EFDB50",
    CSS: "#563D7C",
    HTML: "#E34C26",
    Go: "#00ADD8",
    Rust: "#DEA584",
    Java: "#B07219",
    "C++": "#F34B7D",
    C: "#555555",
    Shell: "#89e051",
    Markdown: "#083fa1",
    JSON: "#29b6f6",
    YAML: "#cb3f85",
  };
  return colors[lang] || "#9b6cf5";
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
}

function Dashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState<AnalyzeResponse | null>(null);
  const [repoUrl, setRepoUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabId>("overview");

  useEffect(() => {
    const cached = sessionStorage.getItem("rhi:data");
    const url = sessionStorage.getItem("rhi:url") || "";
    setRepoUrl(url);
    if (cached) {
      try {
        setData(JSON.parse(cached));
      } catch {
        /* ignore */
      }
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
      <div className="min-h-screen grid place-items-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <RefreshCw className="h-8 w-8 text-primary animate-spin" />
          <span className="text-xs font-semibold text-muted-foreground">Hydrating analysis workspace...</span>
        </div>
      </div>
    );
  }

  // Sidebar Menu Items Definition
  const menuItems = [
    { id: "overview", label: "Overview Summary", icon: LayoutDashboard },
    { id: "file-tree", label: "File Tree Explorer", icon: FolderGit },
    { id: "commits", label: "Commit History", icon: GitCommit },
    { id: "quality", label: "Languages & Hotspots", icon: BarChart3 },
    { id: "risks", label: "Risk Assessment", icon: ShieldAlert },
  ] as const;

  return (
    <div className="relative min-h-screen flex flex-col md:flex-row bg-background">
      {/* Background visual layers */}
      <div className="absolute inset-0 bg-hero opacity-30 pointer-events-none" />
      <div className="absolute inset-0 grid-bg pointer-events-none opacity-40" />

      {/* 1. Premium Sidebar Navigation */}
      <aside className="relative z-20 w-full md:w-64 shrink-0 md:h-screen md:sticky md:top-0 flex flex-col glass-strong border-b md:border-b-0 md:border-r border-border/30 backdrop-blur-xl">
        {/* Sidebar Header / Logo */}
        <div className="px-6 py-5 flex items-center justify-between border-b border-border/20">
          <Logo />
          <Link 
            to="/" 
            className="md:hidden p-1.5 rounded-lg hover:bg-secondary/80 text-muted-foreground hover:text-foreground transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </div>

        {/* Repository context info banner */}
        <div className="px-5 py-4 border-b border-border/10 bg-secondary/20">
          <div className="text-[10px] uppercase font-bold tracking-widest text-muted-foreground">Active Repository</div>
          <div className="text-xs font-semibold text-foreground truncate mt-1 flex items-center gap-1.5">
            <span className="h-1.5 w-1.5 rounded-full bg-success shrink-0" />
            {data.repo_name}
          </div>
        </div>

        {/* Navigation Tabs List */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-xs font-semibold tracking-wide transition-all ${
                  isActive
                    ? "gradient-primary text-white shadow-glow"
                    : "hover:bg-secondary/50 text-muted-foreground hover:text-foreground"
                }`}
              >
                <Icon className={`h-4.5 w-4.5 ${isActive ? "text-white" : "text-muted-foreground group-hover:text-foreground"}`} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Sidebar Footer Controls */}
        <div className="p-4 border-t border-border/10 space-y-2 bg-secondary/10">
          <button
            onClick={handleReanalyze}
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl glass text-xs font-semibold text-foreground hover:bg-secondary/70 transition-colors"
          >
            <RotateCw className="h-3.5 w-3.5" />
            Sync Analysis
          </button>
          <Link
            to="/"
            className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl gradient-secondary text-xs font-semibold text-primary border border-primary/20 hover:shadow-elegant transition-all"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Analyze Another
          </Link>
        </div>
      </aside>

      {/* 2. Main Content Workspace */}
      <main className="flex-1 relative z-10 flex flex-col h-full min-h-screen">
        {/* Global Dashboard Header */}
        <header className="relative z-10 px-6 lg:px-10 py-5 flex items-center justify-between border-b border-border/20 backdrop-blur-md bg-white/10">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-foreground">{data.repo_name}</h1>
            {error && <p className="text-xs text-destructive mt-1">{error}</p>}
          </div>
          <div className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground bg-secondary/80 py-1.5 px-3 rounded-lg border border-border/30">
            Health: {data.health_score}/100
          </div>
        </header>

        {/* Tab Panel Viewport */}
        <div className="flex-1 p-6 lg:p-8 max-w-[1300px] w-full mx-auto space-y-6">
          <AnimatePresence mode="wait">
            {/* Overview Tab Content */}
            {activeTab === "overview" && (
              <motion.div
                key="overview"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
                className="space-y-6"
              >
                {/* Metric cards grid */}
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

                {/* Health Timeline & AI Insight Block */}
                <div className="grid lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2">
                    <HealthTimeline data={data.health_timeline} />
                  </div>
                  <AIInsight insight={data.ai_insight} />
                </div>
              </motion.div>
            )}

            {/* File Tree Explorer Tab Content */}
            {activeTab === "file-tree" && (
              <motion.div
                key="file-tree"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
              >
                <FileGraphTree repoName={data.repo_name} />
              </motion.div>
            )}

            {/* Commit Explorer Tab Content */}
            {activeTab === "commits" && (
              <motion.div
                key="commits"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
              >
                <CommitExplorer commits={data.commits} />
              </motion.div>
            )}

            {/* Languages & Hotspots Tab Content */}
            {activeTab === "quality" && (
              <motion.div
                key="quality"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
                className="grid lg:grid-cols-5 gap-6"
              >
                {/* Left side: Language Breakdown */}
                <div className="lg:col-span-2 rounded-2xl glass-strong glow-border p-6 relative overflow-hidden flex flex-col min-h-[500px]">
                  <div className="absolute -top-32 -left-32 h-80 w-80 rounded-full bg-mesh opacity-10 blur-3xl pointer-events-none" />
                  <div className="space-y-1 pb-4 border-b border-border/30">
                    <h3 className="text-lg font-semibold tracking-tight">Language Distribution</h3>
                    <p className="text-xs text-muted-foreground">Dynamic scan of code volumes and file extensions</p>
                  </div>

                  <div className="flex-1 mt-6 space-y-5 overflow-y-auto max-h-[380px] pr-1 scrollbar-thin">
                    {data.languages && data.languages.length > 0 ? (
                      data.languages.map((item) => (
                        <div key={item.language} className="space-y-1.5 group">
                          <div className="flex items-center justify-between text-xs font-semibold">
                            <span className="text-foreground/90 flex items-center gap-2">
                              <span 
                                className="h-2.5 w-2.5 rounded-full shadow-glow" 
                                style={{ 
                                  background: getLanguageColor(item.language), 
                                  boxShadow: `0 0 6px ${getLanguageColor(item.language)}` 
                                }} 
                              />
                              {item.language}
                            </span>
                            <span className="text-muted-foreground">
                              {item.file_count} file{item.file_count !== 1 ? 's' : ''} ({formatBytes(item.bytes)})
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            <div className="flex-1 h-2.5 bg-secondary/40 rounded-full overflow-hidden">
                              <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${item.percentage}%` }}
                                transition={{ duration: 0.8, ease: "easeOut" }}
                                className="h-full rounded-full transition-all group-hover:brightness-110"
                                style={{ background: getLanguageColor(item.language) }}
                              />
                            </div>
                            <span className="text-[11px] font-bold text-foreground shrink-0 w-10 text-right">
                              {item.percentage}%
                            </span>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-center py-20">
                        <span className="text-3xl">📊</span>
                        <p className="text-xs text-muted-foreground mt-2 font-medium">No language breakdown compiled yet</p>
                      </div>
                    )}
                  </div>
                </div>

                {/* Right side: AI Hotspots Table */}
                <div className="lg:col-span-3 rounded-2xl glass-strong glow-border p-6 relative overflow-hidden flex flex-col min-h-[500px]">
                  <div className="absolute -bottom-32 -right-32 h-80 w-80 rounded-full bg-mesh opacity-10 blur-3xl pointer-events-none" />
                  <div className="space-y-1 pb-4 border-b border-border/30">
                    <h3 className="text-lg font-semibold tracking-tight">AI Hotspots Scoreboard</h3>
                    <p className="text-xs text-muted-foreground">Top high-churn modules flagged by dynamic code complexity audits</p>
                  </div>

                  <div className="flex-1 mt-6 overflow-y-auto max-h-[380px] pr-1 scrollbar-thin space-y-3">
                    {data.hotspots && data.hotspots.length > 0 ? (
                      data.hotspots.map((item) => (
                        <div 
                          key={item.filepath} 
                          className="group flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl glass hover:bg-secondary/40 border border-border/10 transition-all duration-150 gap-3"
                        >
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-foreground font-semibold truncate block">
                                {item.filepath.split('/').pop()}
                              </span>
                              <span className={`text-[9px] font-extrabold uppercase px-1.5 py-0.5 rounded ${
                                item.risk_score >= 70 ? 'bg-red-500/10 text-red-400 border border-red-500/20' :
                                item.risk_score >= 40 ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                                'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                              }`}>
                                {item.risk_score >= 70 ? 'Critical' : item.risk_score >= 40 ? 'Warning' : 'Stable'}
                              </span>
                            </div>
                            <span className="text-[10px] text-muted-foreground font-mono truncate block mt-0.5 select-all">
                              {item.filepath}
                            </span>
                          </div>

                          <div className="flex items-center justify-between sm:justify-end gap-6 shrink-0 text-right text-xs border-t sm:border-t-0 border-border/10 pt-2 sm:pt-0">
                            <div>
                              <div className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider">Commit Churn</div>
                              <div className="font-bold text-foreground mt-0.5">{item.churn} edits</div>
                            </div>
                            <div>
                              <div className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider">Lines Modified</div>
                              <div className="font-bold text-foreground mt-0.5">
                                <span className="text-emerald-400">+{item.insertions.toLocaleString()}</span>
                                <span className="text-muted-foreground mx-1">/</span>
                                <span className="text-red-400">-{item.deletions.toLocaleString()}</span>
                              </div>
                            </div>
                            <div className="w-12 text-center">
                              <div className="text-[9px] uppercase font-bold text-muted-foreground tracking-wider">Risk</div>
                              <div className={`font-extrabold mt-0.5 ${
                                item.risk_score >= 70 ? 'text-red-400' :
                                item.risk_score >= 40 ? 'text-amber-400' :
                                'text-emerald-400'
                              }`}>
                                {item.risk_score}
                              </div>
                            </div>
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="flex flex-col items-center justify-center h-full text-center py-20">
                        <span className="text-3xl">🔥</span>
                        <p className="text-xs text-muted-foreground mt-2 font-medium">No hotspot scoreboard available</p>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Risk Assessment Tab Content */}
            {activeTab === "risks" && (
              <motion.div
                key="risks"
                initial={{ opacity: 0, y: 15 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -15 }}
                transition={{ duration: 0.25 }}
                className="grid lg:grid-cols-3 gap-6"
              >
                <div className="lg:col-span-2">
                  <RiskSection risks={data.risks} />
                </div>
                
                {/* Advanced Static Quality Guide card */}
                <motion.div 
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="rounded-2xl glass-strong glow-border p-6 space-y-4"
                >
                  <div>
                    <h3 className="text-base font-bold tracking-tight">AI Quality Standards</h3>
                    <p className="text-xs text-muted-foreground mt-0.5">Sentinel Prime architectural thresholds</p>
                  </div>
                  <div className="space-y-3.5 text-xs">
                    <div className="flex items-start gap-2.5">
                      <span className="h-5 w-5 rounded-md bg-emerald-500/10 text-emerald-400 grid place-items-center text-[10px] font-bold shrink-0">A</span>
                      <div>
                        <div className="font-semibold text-foreground">Radon Grade A (Complexity &lt; 5)</div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">Ideal codebase health. Modular structure with high test coverage.</div>
                      </div>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <span className="h-5 w-5 rounded-md bg-amber-500/10 text-amber-400 grid place-items-center text-[10px] font-bold shrink-0">B</span>
                      <div>
                        <div className="font-semibold text-foreground">Radon Grade B/C (Complexity 6-15)</div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">Moderate warning. Moderate nested blocks and initial coupling tendencies.</div>
                      </div>
                    </div>
                    <div className="flex items-start gap-2.5">
                      <span className="h-5 w-5 rounded-md bg-red-500/10 text-red-400 grid place-items-center text-[10px] font-bold shrink-0">D</span>
                      <div>
                        <div className="font-semibold text-foreground">Radon Grade D+ (Complexity &gt; 15)</div>
                        <div className="text-[10px] text-muted-foreground mt-0.5">Architectural risk. Requires immediate decomposition and decoupling.</div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Global Footer */}
        <footer className="text-center text-xs text-muted-foreground py-6 border-t border-border/10 bg-secondary/5 mt-auto">
          Repo Health Intelligence · Powered by RAG Vector DB & DeepSeek LLM
        </footer>
      </main>

      {/* Cinematic Full Screen Loader */}
      {loading && <LoadingScreen repo={repoUrl} />}
    </div>
  );
}
