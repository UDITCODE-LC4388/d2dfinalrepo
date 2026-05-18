import { motion } from "framer-motion";

const steps = [
  "Cloning repository metadata",
  "Parsing commit graph",
  "Scoring architectural health",
  "Generating AI insights",
];

export function LoadingScreen({ repo }: { repo: string }) {
  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-background/80 backdrop-blur-xl">
      <div className="absolute inset-0 bg-hero opacity-60" />
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="relative w-[min(92vw,520px)] rounded-3xl glass-strong glow-border p-8 text-center"
      >
        <div className="relative mx-auto h-20 w-20 mb-6">
          <motion.div
            className="absolute inset-0 rounded-full border-2 border-primary/30 border-t-primary"
            animate={{ rotate: 360 }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="absolute inset-2 rounded-full border-2 border-[oklch(0.7_0.2_290)]/20 border-b-[oklch(0.7_0.2_290)]"
            animate={{ rotate: -360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          />
          <div className="absolute inset-0 grid place-items-center">
            <div className="h-3 w-3 rounded-full gradient-primary shadow-glow animate-pulse" />
          </div>
        </div>
        <h2 className="text-xl font-semibold tracking-tight gradient-text">
          Analyzing Repository Intelligence
        </h2>
        <p className="text-sm text-muted-foreground mt-1.5 truncate">{repo}</p>

        <div className="mt-6 space-y-2.5">
          {steps.map((s, i) => (
            <motion.div
              key={s}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.3 + i * 0.4 }}
              className="flex items-center gap-3 text-sm text-foreground/80"
            >
              <motion.span
                className="h-1.5 w-1.5 rounded-full bg-primary"
                animate={{ opacity: [0.3, 1, 0.3] }}
                transition={{ duration: 1.4, repeat: Infinity, delay: i * 0.2 }}
              />
              {s}
            </motion.div>
          ))}
        </div>

        <div className="mt-6 h-1 rounded-full bg-secondary overflow-hidden">
          <motion.div
            className="h-full gradient-primary"
            initial={{ width: "0%" }}
            animate={{ width: ["0%", "60%", "85%", "95%"] }}
            transition={{ duration: 4, times: [0, 0.4, 0.8, 1], ease: "easeOut" }}
          />
        </div>
      </motion.div>
    </div>
  );
}
