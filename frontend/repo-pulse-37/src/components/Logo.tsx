import { Link } from "@tanstack/react-router";

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2.5 group">
      <div className="relative h-9 w-9 rounded-xl gradient-primary shadow-glow grid place-items-center overflow-hidden">
        <div className="absolute inset-0 bg-mesh opacity-40" />
        <svg viewBox="0 0 24 24" className="relative h-5 w-5 text-white" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="6" cy="6" r="2" />
          <circle cx="18" cy="6" r="2" />
          <circle cx="12" cy="18" r="2" />
          <path d="M6 8v2a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2V8" />
          <path d="M12 12v4" />
        </svg>
      </div>
      <div className="leading-tight">
        <div className="text-sm font-semibold tracking-tight text-foreground">Repo Health</div>
        <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">Intelligence</div>
      </div>
    </Link>
  );
}
