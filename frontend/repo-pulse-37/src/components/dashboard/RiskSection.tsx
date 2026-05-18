import { motion } from "framer-motion";
import type { RiskItem } from "@/lib/api";

const sevStyles = {
  high: { bg: "from-[oklch(0.95_0.05_25)] to-[oklch(0.97_0.03_25)]", dot: "oklch(0.65 0.22 25)", label: "High" },
  medium: { bg: "from-[oklch(0.97_0.05_80)] to-[oklch(0.98_0.03_80)]", dot: "oklch(0.78 0.16 80)", label: "Medium" },
  low: { bg: "from-[oklch(0.96_0.04_200)] to-[oklch(0.98_0.02_200)]", dot: "oklch(0.7 0.15 200)", label: "Low" },
};

const typeIcons: Record<string, string> = {
  coupling: "M8 12h8M8 8h8M8 16h5",
  instability: "M12 2L2 22h20L12 2z M12 16v.01",
  drift: "M3 12h18M12 3v18",
  maintainability: "M12 2v20M2 12h20",
};

/** Plain-language labels shown instead of technical type names */
const typeLabels: Record<string, string> = {
  coupling: "Connected modules",
  instability: "Big code changes",
  drift: "Team dependency",
  maintainability: "Code quality",
};

export function RiskSection({ risks }: { risks: RiskItem[] }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.6 }}
      className="rounded-2xl glass-strong glow-border p-6 h-full flex flex-col"
    >
      <div className="flex items-start justify-between gap-3 mb-5 shrink-0">
        <div>
          <h3 className="text-lg font-semibold tracking-tight">Architectural Risks</h3>
          <p className="text-sm text-muted-foreground mt-0.5">{risks.length} signals detected</p>
        </div>
        <span className="text-[10px] uppercase tracking-widest text-primary font-semibold text-right shrink-0">
          DevOps Intelligence
        </span>
      </div>

      <div className="flex flex-col gap-3 w-full flex-1 min-h-0">
        {risks.map((r, i) => {
          const s = sevStyles[r.severity];
          return (
            <motion.div
              key={r.id}
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.06 }}
              whileHover={{ y: -2 }}
              className={`w-full rounded-xl p-4 sm:p-5 bg-gradient-to-br ${s.bg} border border-white/80 shadow-card`}
            >
              <div className="flex items-start gap-3 w-full">
                <div className="h-10 w-10 rounded-lg bg-white grid place-items-center shadow-card shrink-0">
                  <svg
                    viewBox="0 0 24 24"
                    className="h-4 w-4"
                    fill="none"
                    stroke={s.dot}
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <path d={typeIcons[r.type]} />
                  </svg>
                </div>
                <div className="flex-1 min-w-0 w-full">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className="text-[10px] uppercase tracking-widest font-semibold px-2 py-0.5 rounded"
                      style={{ background: `${s.dot}22`, color: s.dot }}
                    >
                      {s.label}
                    </span>
                    <span className="text-[10px] text-muted-foreground">
                      {typeLabels[r.type] ?? r.type}
                    </span>
                  </div>
                  <div className="text-sm font-semibold mt-2 leading-snug">{r.title}</div>
                  <p className="text-xs text-muted-foreground mt-1.5 leading-relaxed">{r.description}</p>
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>
    </motion.div>
  );
}
