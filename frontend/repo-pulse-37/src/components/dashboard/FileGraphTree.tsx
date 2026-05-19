import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  Folder, FolderOpen, File, AlertTriangle, CheckCircle, 
  ChevronRight, ChevronDown, RefreshCw, Code, GitCommit, Link2 
} from "lucide-react";

interface TreeNode {
  name: string;
  type: "file" | "folder";
  path: string;
  risk?: "healthy" | "warning" | "critical";
  complexity?: string;
  churn?: number;
  coupling?: string;
  aiRecommendation?: string;
  children?: TreeNode[];
}

// Rich mock repository codebase structure tailored to show critical files
const INITIAL_TREE_DATA: TreeNode = {
  name: "root",
  type: "folder",
  path: "/",
  children: [
    {
      name: "src",
      type: "folder",
      path: "/src",
      children: [
        {
          name: "components",
          type: "folder",
          path: "/src/components",
          children: [
            {
              name: "SentinelCopilot.tsx",
              type: "file",
              path: "/src/components/SentinelCopilot.tsx",
              risk: "warning",
              complexity: "Radon Grade B (8.4)",
              churn: 14,
              coupling: "High (65%)",
              aiRecommendation: "Consolidate custom state handlers. Delegate history caching and direct network connectivity to a dedicated hooks layer to clean up the view component."
            },
            {
              name: "dashboard",
              type: "folder",
              path: "/src/components/dashboard",
              children: [
                {
                  name: "FileGraphTree.tsx",
                  type: "file",
                  path: "/src/components/dashboard/FileGraphTree.tsx",
                  risk: "healthy",
                  complexity: "Radon Grade A (3.2)",
                  churn: 2,
                  coupling: "Low (12%)",
                  aiRecommendation: "Excellent clean rendering structure using pure visual SVG trees and isolated state. No current refactoring required."
                },
                {
                  name: "HealthTimeline.tsx",
                  type: "file",
                  path: "/src/components/dashboard/HealthTimeline.tsx",
                  risk: "healthy",
                  complexity: "Radon Grade A (2.1)",
                  churn: 4,
                  coupling: "Low (20%)",
                  aiRecommendation: "Highly optimized chart wrapping. Ensure canvas sizing remains responsive on small screens."
                }
              ]
            }
          ]
        },
        {
          name: "lib",
          type: "folder",
          path: "/src/lib",
          children: [
            {
              name: "api.ts",
              type: "file",
              path: "/src/lib/api.ts",
              risk: "healthy",
              complexity: "Radon Grade A (4.5)",
              churn: 9,
              coupling: "Medium (45%)",
              aiRecommendation: "Ensure axios endpoints use central configurations. Decouple absolute URLs into environment environment files."
            }
          ]
        },
        {
          name: "App.tsx",
          type: "file",
          path: "/src/App.tsx",
          risk: "healthy",
          complexity: "Radon Grade A (2.5)",
          churn: 3,
          coupling: "Low (15%)"
        }
      ]
    },
    {
      name: "backend",
      type: "folder",
      path: "/backend",
      children: [
        {
          name: "analyzer",
          type: "folder",
          path: "/backend/analyzer",
          children: [
            {
              name: "vector_db.py",
              type: "file",
              path: "/backend/analyzer/vector_db.py",
              risk: "healthy",
              complexity: "Radon Grade A (4.1)",
              churn: 3,
              coupling: "Low (10%)",
              aiRecommendation: "Lightweight NumPy calculations are fast. Keep stopword parsing in sync with general site search requirements."
            },
            {
              name: "llm_client.py",
              type: "file",
              path: "/backend/analyzer/llm_client.py",
              risk: "healthy",
              complexity: "Radon Grade A (3.8)",
              churn: 2,
              coupling: "Medium (30%)",
              aiRecommendation: "Multi-provider failover strategy is highly robust. Consider moving API endpoints and keys to backend settings schemas."
            },
            {
              name: "ai_summary.py",
              type: "file",
              path: "/backend/analyzer/ai_summary.py",
              risk: "critical",
              complexity: "Radon Grade D (26.4)",
              churn: 32,
              coupling: "Extremely High (85%)",
              aiRecommendation: "CRITICAL COGNITIVE LOAD WARNING. This module suffers from very high commit churn and deep cyclomatic complexity deltas. Split commit-specific heuristic matching into separate parsing modules to restore structural maintainability."
            }
          ]
        },
        {
          name: "main.py",
          type: "file",
          path: "/backend/main.py",
          risk: "warning",
          complexity: "Radon Grade B (9.8)",
          churn: 19,
          coupling: "High (70%)",
          aiRecommendation: "FastAPI server contains multiple raw endpoints. Consider moving business operations out of main.py and utilizing FastAPI's APIRouter structure for cleaner separation of concerns."
        }
      ]
    },
    {
      name: "tests",
      type: "folder",
      path: "/tests",
      children: [
        {
          name: "test_chat_rag.py",
          type: "file",
          path: "/tests/test_chat_rag.py",
          risk: "healthy",
          complexity: "Radon Grade A (1.5)",
          churn: 1
        }
      ]
    },
    {
      name: "README.md",
      type: "file",
      path: "/README.md",
      risk: "healthy",
      complexity: "Radon Grade A (1.0)",
      churn: 5
    },
    {
      name: "package.json",
      type: "file",
      path: "/package.json",
      risk: "healthy",
      complexity: "N/A",
      churn: 8
    }
  ]
};

export function FileGraphTree({ repoName }: { repoName: string }) {
  const [selectedFile, setSelectedFile] = useState<TreeNode | null>(null);
  const [expandedNodes, setExpandedNodes] = useState<Record<string, boolean>>({
    "/": true,
    "/src": true,
    "/backend": true,
    "/backend/analyzer": true,
  });

  const toggleExpand = (path: string) => {
    setExpandedNodes(prev => ({ ...prev, [path]: !prev[path] }));
  };

  const getRiskIcon = (risk?: string) => {
    switch (risk) {
      case "critical":
        return <AlertTriangle className="h-4 w-4 text-red-500 animate-pulse" />;
      case "warning":
        return <AlertTriangle className="h-4 w-4 text-amber-500" />;
      case "healthy":
      default:
        return <CheckCircle className="h-4 w-4 text-emerald-500" />;
    }
  };

  const getRiskBadgeClass = (risk?: string) => {
    switch (risk) {
      case "critical":
        return "bg-red-500/10 text-red-400 border border-red-500/20";
      case "warning":
        return "bg-amber-500/10 text-amber-400 border border-amber-500/20";
      case "healthy":
      default:
        return "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
    }
  };

  // Recursive Tree Node Renderer
  const renderNode = (node: TreeNode, depth: number = 0) => {
    const isFolder = node.type === "folder";
    const isExpanded = expandedNodes[node.path];
    const isSelected = selectedFile?.path === node.path;

    return (
      <div key={node.path} className="select-none">
        {/* Row element */}
        <div
          onClick={() => {
            if (isFolder) {
              toggleExpand(node.path);
            } else {
              setSelectedFile(node);
            }
          }}
          style={{ paddingLeft: `${depth * 18 + 8}px` }}
          className={`group flex items-center py-2 px-3 rounded-lg cursor-pointer transition-all duration-150 ${
            isSelected 
              ? "bg-primary/10 text-primary border-l-2 border-primary" 
              : "hover:bg-secondary/40 text-foreground/80 hover:text-foreground border-l-2 border-transparent"
          }`}
        >
          {/* Collapse Indicator */}
          {isFolder ? (
            <span className="mr-1 text-muted-foreground group-hover:text-foreground">
              {isExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            </span>
          ) : (
            <span className="w-5" />
          )}

          {/* Folder / File Icon */}
          <span className="mr-2 text-muted-foreground shrink-0">
            {isFolder ? (
              isExpanded ? <FolderOpen className="h-4 w-4 text-blue-400" /> : <Folder className="h-4 w-4 text-blue-400" />
            ) : (
              <File className="h-4 w-4 text-slate-400 group-hover:text-slate-200 transition-colors" />
            )}
          </span>

          {/* Text name */}
          <span className={`text-sm font-medium ${isFolder ? "text-foreground" : "text-foreground/90"} flex-1 truncate`}>
            {node.name}
          </span>

          {/* Risk Level Marker */}
          {!isFolder && node.risk && (
            <span className="ml-2 shrink-0 group-hover:scale-105 transition-transform">
              {getRiskIcon(node.risk)}
            </span>
          )}
        </div>

        {/* Child rendering with visual SVG connectors */}
        {isFolder && isExpanded && node.children && (
          <div className="relative">
            {/* Visual connector line */}
            <div 
              style={{ left: `${depth * 18 + 17}px` }} 
              className="absolute top-0 bottom-3 w-[1px] bg-border/40" 
            />
            <div className="mt-0.5">
              {node.children.map(child => renderNode(child, depth + 1))}
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      className="grid lg:grid-cols-5 gap-6 rounded-2xl glass-strong glow-border p-6 overflow-hidden min-h-[500px]"
    >
      {/* Visual background glow elements */}
      <div className="absolute -top-32 -left-32 h-80 w-80 rounded-full bg-mesh opacity-10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 h-80 w-80 rounded-full bg-mesh opacity-10 blur-3xl pointer-events-none" />

      {/* Main File Browser Tree */}
      <div className="lg:col-span-3 flex flex-col h-[520px]">
        <div className="flex items-center justify-between pb-4 border-b border-border/30">
          <div>
            <h3 className="text-lg font-semibold tracking-tight">AI File Architecture Tree</h3>
            <p className="text-xs text-muted-foreground mt-0.5">Interactive visual file hierarchy & static analysis</p>
          </div>
          <span className="px-2.5 py-1 rounded-full bg-secondary/80 text-[10px] uppercase font-bold tracking-wider text-muted-foreground select-none">
            {repoName}
          </span>
        </div>

        {/* Tree container list */}
        <div className="flex-1 overflow-y-auto pr-2 mt-4 space-y-0.5 scrollbar-thin">
          {renderNode(INITIAL_TREE_DATA)}
        </div>
      </div>

      {/* AI Architectural Inspector Panel */}
      <div className="lg:col-span-2 flex flex-col h-[520px] border-t lg:border-t-0 lg:border-l border-border/30 pt-6 lg:pt-0 lg:pl-6">
        <AnimatePresence mode="wait">
          {selectedFile ? (
            <motion.div
              key={selectedFile.path}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              transition={{ duration: 0.2 }}
              className="flex flex-col h-full space-y-5"
            >
              {/* Header Details */}
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className={`text-[10px] uppercase font-extrabold px-2 py-0.5 rounded tracking-wider ${getRiskBadgeClass(selectedFile.risk)}`}>
                    {selectedFile.risk || "Healthy"} RISK
                  </span>
                  <span className="text-[11px] text-muted-foreground font-semibold flex items-center gap-1">
                    <Code className="h-3 w-3" /> Static Analysis
                  </span>
                </div>
                <h4 className="text-xl font-bold tracking-tight text-foreground truncate mt-1">
                  {selectedFile.name}
                </h4>
                <p className="text-xs text-muted-foreground font-medium font-mono bg-secondary/40 py-1.5 px-3 rounded-lg select-all truncate">
                  {selectedFile.path}
                </p>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div className="glass rounded-xl p-3 border border-border/10">
                  <div className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Radon Complexity</div>
                  <div className="text-sm font-bold text-foreground mt-1 flex items-center gap-1.5">
                    <Code className="h-4 w-4 text-primary shrink-0" />
                    {selectedFile.complexity || "Radon Grade A (1.2)"}
                  </div>
                </div>
                <div className="glass rounded-xl p-3 border border-border/10">
                  <div className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Commit Churn</div>
                  <div className="text-sm font-bold text-foreground mt-1 flex items-center gap-1.5">
                    <GitCommit className="h-4 w-4 text-purple-400 shrink-0" />
                    {selectedFile.churn ? `${selectedFile.churn} edits` : "1 edit"}
                  </div>
                </div>
                <div className="glass rounded-xl p-3 border border-border/10 col-span-2">
                  <div className="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">Architectural Coupling</div>
                  <div className="text-sm font-bold text-foreground mt-1 flex items-center gap-1.5">
                    <Link2 className="h-4 w-4 text-blue-400 shrink-0" />
                    {selectedFile.coupling || "Low (8%)"}
                  </div>
                </div>
              </div>

              {/* AI Architecture Insight Card */}
              <div className="flex-1 flex flex-col justify-end">
                <div className="rounded-xl gradient-secondary p-5 border border-border/20 relative overflow-hidden shadow-elegant">
                  <div className="absolute top-0 right-0 h-24 w-24 rounded-full bg-mesh opacity-10 blur-xl pointer-events-none" />
                  <div className="flex items-center gap-2 mb-2 text-xs font-semibold text-primary">
                    <RefreshCw className="h-3.5 w-3.5 animate-spin-slow text-primary" />
                    AI Copilot Recommendation
                  </div>
                  <p className="text-xs text-foreground/80 leading-relaxed font-medium">
                    {selectedFile.aiRecommendation || 
                      "This file exhibits clean dependency modularity and low complexity scores. Continue keeping operations single-purposed and minimize side effects."
                    }
                  </p>
                </div>
              </div>
            </motion.div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-6 border border-dashed border-border/30 rounded-2xl bg-secondary/5">
              <div className="h-12 w-12 rounded-full gradient-primary/10 flex items-center justify-center text-primary mb-4 shadow-sm">
                🤖
              </div>
              <h4 className="text-sm font-semibold text-foreground">No File Selected</h4>
              <p className="text-xs text-muted-foreground max-w-[200px] mt-1.5 leading-relaxed font-medium">
                Click on any file node in the left repository tree to inspect its cyclomatic complexity and AI architectural recommendation cards.
              </p>
            </div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
