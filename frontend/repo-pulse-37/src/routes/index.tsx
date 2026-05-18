import { createFileRoute, useNavigate } from "@tanstack/react-router";
import axios from "axios";
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { AnimatedBackground } from "@/components/AnimatedBackground";
import { Logo } from "@/components/Logo";
import { LoadingScreen } from "@/components/LoadingScreen";
import { analyzeRepo } from "@/lib/api";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Repo Health Intelligence — AI-powered repository analytics" },
      { name: "description", content: "Track how your codebase evolves. AI-powered repository intelligence for architectural health, maintainability, and engineering risk analysis." },
      { property: "og:title", content: "Repo Health Intelligence" },
      { property: "og:description", content: "AI-powered repository intelligence for architectural health and engineering risk analysis." },
    ],
  }),
  component: Landing,
});

const DEFAULT_REPO_URL = "https://github.com/facebook/react";

function Landing() {
  const navigate = useNavigate();
  const [mounted, setMounted] = useState(false);
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUrl(DEFAULT_REPO_URL);
    setMounted(true);
  }, []);

  const handleAnalyze = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const data = await analyzeRepo(url.trim());
      sessionStorage.setItem("rhi:data", JSON.stringify(data));
      sessionStorage.setItem("rhi:url", url.trim());
      // brief cinematic delay for premium feel
      setTimeout(() => navigate({ to: "/dashboard" }), 1500);
    } catch (err) {
      console.error(err);
      const message =
        axios.isAxiosError(err) && err.response?.data?.detail
          ? String(err.response.data.detail)
          : "Could not analyze repository. Is the backend running on port 8000?";
      setError(message);
      setLoading(false);
    }
  };

  return (
    <div className="relative min-h-screen overflow-hidden">
      <AnimatedBackground />

      {/* Nav */}
      <header className="relative z-10 px-6 lg:px-10 pt-6 flex items-center justify-between">
        <Logo />
        <nav className="hidden md:flex items-center gap-7 text-sm text-muted-foreground">
          <a href="#features" className="hover:text-foreground transition">Features</a>
          <a href="#how" className="hover:text-foreground transition">How it works</a>
          <a href="#api" className="hover:text-foreground transition">API</a>
        </nav>
        <a
          href="https://github.com"
          target="_blank"
          rel="noreferrer"
          className="hidden sm:inline-flex items-center gap-2 px-3.5 py-2 rounded-xl glass text-sm font-medium hover:shadow-elegant transition"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="currentColor"><path d="M12 .5C5.65.5.5 5.66.5 12.02c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.55v-2c-3.2.7-3.88-1.36-3.88-1.36-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.16-1.18 3.16-1.18.63 1.59.24 2.76.12 3.05.74.81 1.18 1.84 1.18 3.1 0 4.42-2.7 5.4-5.27 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.66.8.55A11.51 11.51 0 0 0 23.5 12C23.5 5.66 18.35.5 12 .5z" /></svg>
          Star on GitHub
        </a>
      </header>

      {/* Hero */}
      <main className="relative z-10 px-6 lg:px-10 pt-24 pb-32 max-w-6xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex justify-center"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs font-medium text-muted-foreground">
            <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
            AI engineering intelligence · v1.0
          </div>
        </motion.div>

        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.7 }}
          className="mt-6 text-center text-5xl sm:text-6xl lg:text-7xl font-semibold tracking-[-0.03em] leading-[1.05]"
        >
          <span className="gradient-text">Track How Your</span>
          <br />
          <span className="gradient-text">Codebase Evolves.</span>
        </motion.h1>

        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.7 }}
          className="mt-6 text-center text-lg text-muted-foreground max-w-2xl mx-auto leading-relaxed"
        >
          AI-powered repository intelligence for architectural health, maintainability,
          and engineering risk analysis.
        </motion.p>

        {/* CTA Form */}
        <motion.form
          onSubmit={handleAnalyze}
          initial={mounted ? { opacity: 0, y: 20 } : false}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35, duration: 0.7 }}
          className="mt-10 max-w-2xl mx-auto"
        >
          <div className="relative group">
            <div className="absolute -inset-0.5 rounded-2xl gradient-primary opacity-30 blur-lg group-hover:opacity-60 transition-opacity" />
            <div className="relative flex items-center gap-2 rounded-2xl glass-strong p-2 pl-5">
              <svg viewBox="0 0 24 24" className="h-5 w-5 text-muted-foreground shrink-0" fill="currentColor"><path d="M12 .5C5.65.5.5 5.66.5 12.02c0 5.08 3.29 9.39 7.86 10.91.58.1.79-.25.79-.55v-2c-3.2.7-3.88-1.36-3.88-1.36-.52-1.32-1.27-1.67-1.27-1.67-1.04-.71.08-.7.08-.7 1.15.08 1.76 1.18 1.76 1.18 1.02 1.76 2.69 1.25 3.35.96.1-.74.4-1.25.73-1.54-2.55-.29-5.24-1.28-5.24-5.69 0-1.26.45-2.29 1.18-3.1-.12-.29-.51-1.46.11-3.05 0 0 .97-.31 3.17 1.18a11 11 0 0 1 5.78 0c2.2-1.49 3.16-1.18 3.16-1.18.63 1.59.24 2.76.12 3.05.74.81 1.18 1.84 1.18 3.1 0 4.42-2.7 5.4-5.27 5.68.41.36.78 1.06.78 2.14v3.17c0 .31.21.66.8.55A11.51 11.51 0 0 0 23.5 12C23.5 5.66 18.35.5 12 .5z" /></svg>
              <input
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://github.com/owner/repo"
                suppressHydrationWarning
                className="flex-1 bg-transparent outline-none text-sm py-3 placeholder:text-muted-foreground/60"
              />
              <motion.button
                whileTap={{ scale: 0.97 }}
                type="submit"
                disabled={loading || !url}
                suppressHydrationWarning
                className="relative inline-flex items-center gap-2 px-5 py-3 rounded-xl gradient-primary text-white text-sm font-semibold shadow-glow hover:shadow-[0_0_50px_-5px_oklch(0.6_0.2_255/0.6)] transition-all disabled:opacity-60"
              >
                Analyze Repository
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14M13 5l7 7-7 7" /></svg>
              </motion.button>
            </div>
          </div>
          {error && <p className="mt-3 text-sm text-destructive text-center">{error}</p>}
          <p className="mt-3 text-xs text-center text-muted-foreground">
            Try <button type="button" suppressHydrationWarning onClick={() => setUrl("https://github.com/vercel/next.js")} className="underline hover:text-foreground">vercel/next.js</button> · <button type="button" suppressHydrationWarning onClick={() => setUrl("https://github.com/facebook/react")} className="underline hover:text-foreground">facebook/react</button>
          </p>
        </motion.form>

        {/* Feature pills */}
        <motion.div
          id="features"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.7 }}
          className="mt-20 grid sm:grid-cols-3 gap-4 max-w-4xl mx-auto"
        >
          {[
            { t: "Health Scoring", d: "Per-commit health with trend analysis" },
            { t: "Knowledge Graph", d: "Devs, modules, and dependencies visualized" },
            { t: "AI Insights", d: "Explain drops, drift, and architectural risks" },
          ].map((f, i) => (
            <motion.div
              key={f.t}
              whileHover={{ y: -3 }}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.6 + i * 0.08 }}
              className="rounded-2xl glass p-5"
            >
              <div className="h-8 w-8 rounded-lg gradient-primary shadow-glow mb-3" />
              <div className="text-sm font-semibold">{f.t}</div>
              <div className="text-xs text-muted-foreground mt-1">{f.d}</div>
            </motion.div>
          ))}
        </motion.div>
      </main>

      {loading && <LoadingScreen repo={url} />}
    </div>
  );
}
