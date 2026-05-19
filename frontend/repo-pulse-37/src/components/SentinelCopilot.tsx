import { useState, useRef, useEffect } from "react";
import { sendChatMessage } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  sources?: string[];
  modelUsed?: string;
}

const SYSTEM_PROMPT = `
You are Sentinel Copilot, a senior software architect AI assistant built directly into the "Repository Health Intelligence" (Sentinel Prime) platform.
Your goal is to interact with users, explain platform concepts, and answer general coding or architectural questions.

About Repository Health Intelligence:
- Purpose: Unified engineering intelligence platform that mines git commit history, computes codebase hotspots, maps developer-commit collaboration graphs, and extracts relative dependency graphs.
- Health Score (Index): An overall score out of 100 representing the codebase health. High scores (>85) represent healthy structures. Scores are computed based on commit size, file complexity deltas, and architectural dependencies.
- Code Health: Derived from complexity deltas and file churn.
- Team Health / Bus Factor: Represents ownership concentration. A low bus factor (<3) means only 1 or 2 developers are doing all the work, posing a business risk.
- Architecture Health & Stability: Extracted from import dependencies. Stable architectures minimize cyclic dependencies and circular imports.
- Hotspots: Files with both high churn (frequent modifications) and high complexity. These are the main risk vectors in a codebase.
- Collaboration Graph: Visualizes which developers are working on which commits/files, showing knowledge silos or high collaboration clusters.
- AI Summaries: Real-time, context-driven RAG AI analysis powered by the Backend API (supporting DeepSeek and Groq).

When a user asks:
- Website/Platform questions: Explain them clearly in simple but detailed architectural terms.
- General coding or repository health questions: Provide precise, expert-level engineering answers.
- Keep your tone professional, friendly, helpful, and concise. Do not use complex markdown formatting or HTML. Use plain text or light bullets where appropriate.
`;

export function SentinelCopilot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hello! I'm Sentinel Copilot, your architectural intelligence assistant. Ask me anything about repository health scoring, bus factors, hotspots, or general software engineering questions!",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === "function") {
      try {
        messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
      } catch (err) {
        console.warn("scrollIntoView failed:", err);
      }
    }
  }, [messages]);

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      // Build proper history mapped to api type format
      const historyPayload = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      // Call our custom backend API that processes Vector DB RAG + Open Source LLMs
      const response = await sendChatMessage(userMessage, historyPayload);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          sources: response.sources,
          modelUsed: response.model_used,
        },
      ]);
    } catch (err) {
      console.error("Backend Chat API error:", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "I'm sorry, I encountered an error communicating with the Sentinel intelligence backend. Please verify your connection or try again shortly.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Floating Toggle Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative flex items-center justify-center h-14 w-14 rounded-full gradient-primary text-white shadow-glow hover:shadow-[0_0_35px_oklch(0.6_0.2_255/0.8)] hover:scale-105 active:scale-95 transition-all duration-200 outline-none border border-white/10"
      >
        {isOpen ? (
          <svg
            viewBox="0 0 24 24"
            className="h-6 w-6 transition-all duration-200"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        ) : (
          <svg
            viewBox="0 0 24 24"
            className="h-6 w-6 transition-all duration-200"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
          </svg>
        )}
        {/* Glow Notification Pulse */}
        {!isOpen && (
          <span className="absolute top-0 right-0 flex h-3.5 w-3.5">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-success opacity-75"></span>
            <span className="relative inline-flex rounded-full h-3.5 w-3.5 bg-success"></span>
          </span>
        )}
      </button>

      {/* Chat Window Panel */}
      <div
        className={`absolute bottom-20 right-0 w-[350px] sm:w-[400px] h-[500px] rounded-2xl glass-strong border border-border/40 overflow-hidden flex flex-col shadow-elegant backdrop-blur-2xl bg-white/80 transition-all duration-300 transform origin-bottom-right ${
          isOpen
            ? "opacity-100 scale-100 translate-y-0 pointer-events-auto"
            : "opacity-0 scale-95 translate-y-4 pointer-events-none"
        }`}
      >
        {/* Header */}
        <div className="px-5 py-4 border-b border-border/40 flex items-center justify-between bg-white/40">
          <div className="flex items-center gap-3">
            <div className="h-8 w-8 rounded-full gradient-primary flex items-center justify-center text-white text-sm font-semibold shadow-glow">
              🤖
            </div>
            <div>
              <div className="text-sm font-semibold text-foreground flex items-center gap-1.5">
                Sentinel Copilot
                <span className="h-1.5 w-1.5 rounded-full bg-success animate-pulse" />
              </div>
              <div className="text-[10px] text-muted-foreground font-medium uppercase tracking-wider">
                Serverless AI Assistant
              </div>
            </div>
          </div>
          <button
            onClick={() => setIsOpen(false)}
            className="text-muted-foreground hover:text-foreground transition p-1 hover:bg-secondary/40 rounded-lg"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M19 9l-7 7-7-7" /></svg>
          </button>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-5 space-y-4 bg-secondary/10">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`flex flex-col space-y-1 ${m.role === "user" ? "items-end" : "items-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
                  m.role === "user"
                    ? "gradient-primary text-white rounded-br-none font-medium"
                    : "glass text-foreground rounded-bl-none border border-border/10"
                }`}
              >
                <div className="whitespace-pre-wrap">{m.content}</div>

                {/* Sources Section */}
                {m.role === "assistant" && m.sources && m.sources.length > 0 && (
                  <div className="mt-2.5 pt-2 border-t border-border/20 text-[11px] text-muted-foreground select-none">
                    <details className="cursor-pointer group">
                      <summary className="font-semibold flex items-center gap-1 list-none focus:outline-none hover:text-foreground transition-colors">
                        <svg
                          viewBox="0 0 24 24"
                          className="h-3 w-3 transition-transform group-open:rotate-180"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2.5"
                        >
                          <path d="M19 9l-7 7-7-7" />
                        </svg>
                        Sources retrieved from Vector DB ({m.sources.length})
                      </summary>
                      <ul className="mt-1.5 pl-3 list-disc space-y-0.5 text-muted-foreground/80 font-medium leading-normal">
                        {m.sources.map((s, idx) => (
                          <li key={idx}>{s}</li>
                        ))}
                      </ul>
                    </details>
                  </div>
                )}
              </div>

              {/* Model Badge */}
              {m.role === "assistant" && m.modelUsed && (
                <div className="text-[9px] text-muted-foreground/60 font-semibold mt-0.5 px-1.5 flex items-center gap-1 select-none">
                  <span>Processed by</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[8px] uppercase tracking-wider font-bold ${
                      m.modelUsed.includes("DeepSeek")
                        ? "bg-blue-500/10 text-blue-400 border border-blue-500/25"
                        : m.modelUsed.includes("Groq")
                        ? "bg-amber-500/10 text-amber-400 border border-amber-500/25"
                        : "bg-secondary/40 text-muted-foreground border border-border/25"
                    }`}
                  >
                    {m.modelUsed.includes("DeepSeek") ? "⚡ " : m.modelUsed.includes("Groq") ? "🔥 " : "🔌 "}
                    {m.modelUsed}
                  </span>
                </div>
              )}
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="glass rounded-2xl rounded-bl-none px-4 py-3 shadow-sm flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.3s]"></span>
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce [animation-delay:-0.15s]"></span>
                <span className="h-2 w-2 rounded-full bg-primary animate-bounce"></span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Form */}
        <form
          onSubmit={handleSend}
          className="p-3 border-t border-border/40 flex items-center gap-2 bg-white/40"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about health index, hotspots..."
            disabled={loading}
            className="flex-1 bg-secondary/30 outline-none text-sm py-2.5 px-4 rounded-xl border border-border/20 placeholder:text-muted-foreground/60 text-foreground"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-2.5 rounded-xl gradient-primary text-white shadow-glow disabled:opacity-50 transition"
          >
            <svg
              viewBox="0 0 24 24"
              className="h-5 w-5"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
