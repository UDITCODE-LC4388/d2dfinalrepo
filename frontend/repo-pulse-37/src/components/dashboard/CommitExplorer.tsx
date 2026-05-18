import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import type { Commit } from "@/lib/api";

function scoreColor(s: number) {
  if (s >= 80) return "oklch(0.7 0.18 155)";
  if (s >= 60) return "oklch(0.78 0.16 80)";
  return "oklch(0.65 0.22 25)";
}

export function CommitExplorer({ commits }: { commits: Commit[] }) {
  const [open, setOpen] = useState<string | null>(null);
  const [limit, setLimit] = useState(10);
  const visible = commits.slice(0, limit);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 }}
      className="rounded-2xl glass-strong glow-border p-6"
    >
      <div className="flex items-center justify-between mb-5">
        <div>
          <h3 className="text-lg font-semibold tracking-tight">Commit Explorer</h3>
          <p className="text-sm text-muted-foreground mt-0.5">{commits.length} commits analyzed</p>
        </div>
      </div>
      <div className="space-y-2">
        {visible.map((c, i) => {
          const isOpen = open === c.hash;
          return (
            <motion.div
              key={c.hash}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.03 }}
              className="rounded-xl border border-border/60 bg-white/60 hover:bg-white transition-colors overflow-hidden"
            >
              <button
                onClick={() => setOpen(isOpen ? null : c.hash)}
                className="w-full px-4 py-3 flex items-center gap-4 text-left"
              >
                <div
                  className="h-9 w-9 rounded-lg grid place-items-center text-xs font-semibold text-white shrink-0"
                  style={{ background: `linear-gradient(135deg, ${scoreColor(c.health_score)}, ${scoreColor(c.health_score)} 70%)` }}
                >
                  {c.health_score}
                </div>
                <code className="text-xs font-mono text-muted-foreground shrink-0">{c.hash}</code>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{c.message}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {c.author} · {c.files_changed} files · <span className="text-[oklch(0.6_0.18_155)]">+{c.insertions}</span> <span className="text-[oklch(0.6_0.22_25)]">−{c.deletions}</span>
                  </div>
                </div>
                <motion.svg animate={{ rotate: isOpen ? 180 : 0 }} className="h-4 w-4 text-muted-foreground shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M6 9l6 6 6-6" />
                </motion.svg>
              </button>
              <AnimatePresence initial={false}>
                {isOpen && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25 }}
                    className="overflow-hidden border-t border-border/60"
                  >
                    <div className="px-4 py-4 bg-gradient-to-br from-[oklch(0.98_0.01_255)] to-transparent">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="h-5 w-5 rounded-md gradient-primary grid place-items-center">
                          <svg viewBox="0 0 24 24" className="h-3 w-3 text-white" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M12 2v4M12 18v4M4 12H2M22 12h-2" /></svg>
                        </div>
                        <span className="text-[11px] uppercase tracking-widest text-primary font-semibold">AI Explanation</span>
                      </div>
                      <p className="text-sm leading-relaxed text-foreground/75">{c.ai_explanation}</p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          );
        })}
      </div>
      {limit < commits.length && (
        <button
          onClick={() => setLimit((l) => l + 20)}
          className="mt-4 w-full py-2.5 rounded-xl border border-border/60 text-sm font-medium text-muted-foreground hover:bg-white transition"
        >
          Load more commits
        </button>
      )}
    </motion.div>
  );
}
