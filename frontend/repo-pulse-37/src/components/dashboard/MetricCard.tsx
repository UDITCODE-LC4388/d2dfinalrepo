import { motion } from "framer-motion";
import type { ReactNode } from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  suffix?: string;
  icon: ReactNode;
  tone?: "primary" | "success" | "warning" | "danger";
  delta?: string;
  index?: number;
}

const toneStyles: Record<string, string> = {
  primary: "from-[oklch(0.65_0.2_255)] to-[oklch(0.7_0.2_290)]",
  success: "from-[oklch(0.7_0.18_155)] to-[oklch(0.7_0.18_200)]",
  warning: "from-[oklch(0.78_0.16_80)] to-[oklch(0.72_0.2_50)]",
  danger: "from-[oklch(0.7_0.2_25)] to-[oklch(0.65_0.22_15)]",
};

export function MetricCard({ label, value, suffix, icon, tone = "primary", delta, index = 0 }: MetricCardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.08, duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      whileHover={{ y: -4 }}
      className="group relative rounded-2xl glass-strong glow-border p-5 overflow-hidden cursor-default"
    >
      <div className={`absolute -top-16 -right-16 h-40 w-40 rounded-full bg-gradient-to-br ${toneStyles[tone]} opacity-20 blur-2xl group-hover:opacity-40 transition-opacity duration-500`} />
      <div className="flex items-start justify-between relative">
        <div className={`h-10 w-10 rounded-xl bg-gradient-to-br ${toneStyles[tone]} grid place-items-center text-white shadow-glow`}>
          {icon}
        </div>
        {delta && (
          <span className="text-[11px] font-medium text-muted-foreground bg-secondary/60 px-2 py-1 rounded-full">
            {delta}
          </span>
        )}
      </div>
      <div className="mt-5 relative">
        <div className="text-[11px] uppercase tracking-[0.14em] text-muted-foreground font-medium">{label}</div>
        <div className="mt-1.5 flex items-baseline gap-1">
          <motion.span
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: index * 0.08 + 0.2 }}
            className="text-3xl font-semibold tracking-tight gradient-text"
          >
            {value}
          </motion.span>
          {suffix && <span className="text-sm text-muted-foreground">{suffix}</span>}
        </div>
      </div>
    </motion.div>
  );
}
