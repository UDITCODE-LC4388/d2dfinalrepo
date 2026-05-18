import { motion } from "framer-motion";

export function AnimatedBackground() {
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden">
      <div className="absolute inset-0 bg-hero" />
      <div className="absolute inset-0 grid-bg" />
      {[...Array(6)].map((_, i) => (
        <motion.div
          key={i}
          className="absolute rounded-full blur-3xl opacity-40"
          style={{
            width: 280 + i * 60,
            height: 280 + i * 60,
            left: `${(i * 17) % 90}%`,
            top: `${(i * 23) % 70}%`,
            background:
              i % 2 === 0
                ? "radial-gradient(circle, oklch(0.78 0.18 255 / 0.4), transparent 70%)"
                : "radial-gradient(circle, oklch(0.8 0.16 290 / 0.35), transparent 70%)",
          }}
          animate={{
            x: [0, 30, -20, 0],
            y: [0, -25, 15, 0],
          }}
          transition={{ duration: 14 + i * 2, repeat: Infinity, ease: "easeInOut" }}
        />
      ))}
      {/* floating network dots */}
      <svg className="absolute inset-0 h-full w-full opacity-[0.35]">
        <defs>
          <linearGradient id="line-grad" x1="0" x2="1">
            <stop offset="0%" stopColor="oklch(0.65 0.2 255)" stopOpacity="0.6" />
            <stop offset="100%" stopColor="oklch(0.7 0.2 290)" stopOpacity="0" />
          </linearGradient>
        </defs>
        {[...Array(12)].map((_, i) => {
          const x1 = (i * 83) % 100;
          const y1 = (i * 47) % 100;
          const x2 = (x1 + 25) % 100;
          const y2 = (y1 + 18) % 100;
          return (
            <g key={i}>
              <line x1={`${x1}%`} y1={`${y1}%`} x2={`${x2}%`} y2={`${y2}%`} stroke="url(#line-grad)" strokeWidth="1" />
              <circle cx={`${x1}%`} cy={`${y1}%`} r="2.5" fill="oklch(0.6 0.2 255)" />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
