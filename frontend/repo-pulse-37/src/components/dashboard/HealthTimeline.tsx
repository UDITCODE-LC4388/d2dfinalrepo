import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { motion } from "framer-motion";
import { ClientOnly } from "@/components/ClientOnly";

interface Props {
  data: { commit: number; score: number; date: string }[];
}

function Chart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={300}>
      <AreaChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: -20 }}>
        <defs>
          <linearGradient id="healthFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="oklch(0.6 0.2 255)" stopOpacity={0.45} />
            <stop offset="100%" stopColor="oklch(0.6 0.2 255)" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="healthStroke" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="oklch(0.6 0.2 255)" />
            <stop offset="100%" stopColor="oklch(0.65 0.2 290)" />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="oklch(0.9 0.01 250)" strokeDasharray="3 6" vertical={false} />
        <XAxis dataKey="commit" tick={{ fontSize: 11, fill: "oklch(0.5 0.02 260)" }} axisLine={false} tickLine={false} />
        <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "oklch(0.5 0.02 260)" }} axisLine={false} tickLine={false} />
        <Tooltip
          contentStyle={{
            background: "oklch(1 0 0 / 0.95)",
            border: "1px solid oklch(0.9 0.01 250)",
            borderRadius: 12,
            boxShadow: "0 10px 30px -10px oklch(0.3 0.1 260 / 0.18)",
            fontSize: 12,
          }}
          labelStyle={{ color: "oklch(0.4 0.02 260)", fontWeight: 500 }}
        />
        <Area
          type="monotone"
          dataKey="score"
          stroke="url(#healthStroke)"
          strokeWidth={2.5}
          fill="url(#healthFill)"
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function HealthTimeline({ data }: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3, duration: 0.6 }}
      className="rounded-2xl glass-strong glow-border p-6 relative overflow-hidden"
    >
      <div className="flex items-start justify-between mb-5">
        <div>
          <h3 className="text-lg font-semibold tracking-tight">Health Timeline</h3>
          <p className="text-sm text-muted-foreground mt-0.5">Commit health score progression</p>
        </div>
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-[oklch(0.6_0.2_255)] shadow-glow" />
            <span className="text-muted-foreground">Health</span>
          </div>
        </div>
      </div>
      <div className="h-[300px] w-full min-h-[300px]">
        <ClientOnly fallback={<motion.div className="h-full w-full rounded-xl bg-muted/20 animate-pulse" />}>
          <Chart data={data} />
        </ClientOnly>
      </div>
    </motion.div>
  );
}
