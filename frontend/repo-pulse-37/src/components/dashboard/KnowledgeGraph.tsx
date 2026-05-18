import { useEffect, useRef } from "react";
import cytoscape from "cytoscape";
import { motion } from "framer-motion";
import { ClientOnly } from "@/components/ClientOnly";
import type { GraphData } from "@/lib/api";

const typeColors: Record<string, string> = {
  developer: "#5b8def",
  commit: "#9b6cf5",
  module: "#3aa8c9",
  dependency: "#f59e0b",
};

function sanitizeId(id: string, prefix: string) {
  return `${prefix}-${id.replace(/[^a-zA-Z0-9_-]/g, "_")}`;
}

function GraphCanvas({ data }: { data: GraphData }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = ref.current;
    if (!container || data.nodes.length === 0) return;

    let cancelled = false;
    let cy: cytoscape.Core | null = null;

    const nodeIdMap = new Map<string, string>();
    data.nodes.forEach((n, i) => {
      nodeIdMap.set(n.id, sanitizeId(n.id || `node-${i}`, "n"));
    });

    const frameId = requestAnimationFrame(() => {
      if (cancelled || !ref.current) return;

      const elements = [
        ...data.nodes.map((n) => ({
          data: {
            id: nodeIdMap.get(n.id)!,
            label: n.label,
            type: n.type,
          },
        })),
        ...data.edges.map((e, i) => ({
          data: {
            id: e.id || `e${i}`,
            source: nodeIdMap.get(e.source) ?? sanitizeId(e.source, "n"),
            target: nodeIdMap.get(e.target) ?? sanitizeId(e.target, "n"),
          },
        })),
      ];

      cy = cytoscape({
        container: ref.current,
        elements,
        style: [
          {
            selector: "node",
            style: {
              "background-color": (ele: cytoscape.NodeSingular) =>
                typeColors[ele.data("type") as string] || "#5b8def",
              label: "data(label)",
              "font-size": 10,
              "font-weight": 500,
              color: "#334",
              "text-valign": "bottom",
              "text-margin-y": 6,
              width: 28,
              height: 28,
              "border-width": 2,
              "border-color": "#fff",
              "border-opacity": 0.9,
              "overlay-opacity": 0,
            },
          },
          {
            selector: "node:selected",
            style: { "border-color": "#5b8def", "border-width": 3, width: 36, height: 36 },
          },
          {
            selector: "edge",
            style: {
              width: 1.2,
              "line-color": "#c6d2eb",
              "curve-style": "bezier",
              "target-arrow-shape": "triangle",
              "target-arrow-color": "#c6d2eb",
              "arrow-scale": 0.8,
              opacity: 0.7,
            },
          },
          {
            selector: "edge:selected",
            style: {
              "line-color": "#5b8def",
              "target-arrow-color": "#5b8def",
              opacity: 1,
              width: 2,
            },
          },
        ],
        layout: {
          name: "cose",
          animate: false,
          padding: 30,
          idealEdgeLength: 90,
        } as cytoscape.LayoutOptions,
        minZoom: 0.3,
        maxZoom: 2.5,
      });
    });

    return () => {
      cancelled = true;
      cancelAnimationFrame(frameId);
      if (cy) {
        cy.stop();
        cy.destroy();
        cy = null;
      }
    };
  }, [data]);

  return (
    <div
      ref={ref}
      className="h-[460px] w-full min-h-[460px] rounded-xl border border-border/50 bg-gradient-to-br from-[oklch(0.99_0.005_250)] to-[oklch(0.97_0.01_250)]"
    />
  );
}

export function KnowledgeGraph({ data }: { data: GraphData }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.5 }}
      className="rounded-2xl glass-strong glow-border p-6 relative overflow-hidden"
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold tracking-tight">Knowledge Graph</h3>
          <p className="text-sm text-muted-foreground mt-0.5">Developers · Commits</p>
        </div>
        <div className="flex items-center gap-3 text-[11px]">
          {Object.entries(typeColors).map(([k, v]) => (
            <div key={k} className="flex items-center gap-1.5 capitalize text-muted-foreground">
              <span className="h-2 w-2 rounded-full" style={{ background: v, boxShadow: `0 0 8px ${v}` }} />
              {k}
            </div>
          ))}
        </div>
      </div>
      <ClientOnly fallback={<div className="h-[460px] w-full min-h-[460px] rounded-xl bg-muted/20 animate-pulse" />}>
        <GraphCanvas data={data} />
      </ClientOnly>
    </motion.div>
  );
}
