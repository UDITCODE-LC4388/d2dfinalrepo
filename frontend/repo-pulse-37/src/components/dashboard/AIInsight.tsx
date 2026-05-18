import { motion } from "framer-motion";
import { useEffect, useState } from "react";

export function AIInsight({ insight }: { insight: string }) {
  const [typed, setTyped] = useState("");
  useEffect(() => {
    setTyped("");
    let i = 0;
    const id = setInterval(() => {
      i += 3;
      setTyped(insight.slice(0, i));
      if (i >= insight.length) clearInterval(id);
    }, 18);
    return () => clearInterval(id);
  }, [insight]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.4 }}
      className="rounded-2xl glass-strong glow-border p-6 relative overflow-hidden"
    >
      <div className="absolute -top-24 -right-24 h-64 w-64 rounded-full bg-mesh opacity-20 blur-3xl animate-pulse-glow" />
      <div className="flex items-center gap-3 mb-4 relative">
        <div className="h-9 w-9 rounded-xl gradient-primary grid place-items-center shadow-glow">
          <svg viewBox="0 0 24 24" className="h-4 w-4 text-white" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
        </div>
        <div>
          <h3 className="text-base font-semibold tracking-tight">AI Engineering Insight</h3>
          <p className="text-xs text-muted-foreground">Why did repository health drop?</p>
        </div>
        <span className="ml-auto text-[10px] uppercase tracking-widest text-primary font-semibold flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-primary animate-pulse" />
          Live
        </span>
      </div>
      <div className="relative text-sm leading-relaxed text-foreground/80">
        {typed}
        <span className="inline-block w-[2px] h-4 ml-0.5 bg-primary align-middle animate-pulse" />
      </div>
    </motion.div>
  );
}
