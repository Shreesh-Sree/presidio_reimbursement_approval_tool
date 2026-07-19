import { useState, useRef, useEffect } from "react";
import { Sparkle, X, PaperPlaneRight, Robot, User, Quotes } from "@phosphor-icons/react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthContext";
import { policiesApi, type PolicyAssistantAskResponse } from "../../lib/api";

type Message = {
  id: string;
  sender: "user" | "ai";
  text: string;
  citations?: Array<{ excerpt: string; source_chunk_id: string }>;
  timestamp: string;
};

export function RoleAwareAIChatbot() {
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const primaryRole = (user?.roles?.[0] || "Employee").toLowerCase();
  const roleTitle = primaryRole === "admin" || primaryRole === "administrator" 
    ? "Admin AI Advisor" 
    : primaryRole === "manager" 
    ? "Manager AI Compliance" 
    : "Employee AI Assistant";

  // Fetch active policies to obtain policy_id for RAG query
  const policiesQuery = useQuery({
    queryKey: ["policies"],
    queryFn: policiesApi.list,
    enabled: isOpen,
  });

  const activePolicyId = policiesQuery.data?.[0]?.id;

  const askMutation = useMutation({
    mutationFn: async (questionText: string) => {
      if (!activePolicyId) {
        throw new Error("No active policy document found to query.");
      }
      return policiesApi.askAssistant(activePolicyId, { question: questionText });
    },
    onSuccess: (data: PolicyAssistantAskResponse, variables: string) => {
      const aiMsg: Message = {
        id: Math.random().toString(36).substring(2),
        sender: "ai",
        text: data.answer,
        citations: data.citations?.map((c) => ({ excerpt: c.excerpt, source_chunk_id: c.source_chunk_id })),
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, aiMsg]);
    },
    onError: (err: Error) => {
      const errorMsg: Message = {
        id: Math.random().toString(36).substring(2),
        sender: "ai",
        text: err.message || "I could not answer that question based on current policy evidence.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    },
  });

  useEffect(() => {
    if (messages.length === 0 && user) {
      let welcomeText = "Hello! I am your AI Expense & Policy Assistant. Ask me anything about claiming expenses, travel caps, or receipt requirements.";
      if (primaryRole.includes("admin")) {
        welcomeText = "Hello Admin! I am your System & Policy AI Advisor. Ask me about system workflow routing, access approvals, or policy document indexing.";
      } else if (primaryRole.includes("manager")) {
        welcomeText = "Hello Manager! I am your AI Compliance Advisor. Ask me about approval checks, policy violation flags, or delegation rules.";
      }
      setMessages([
        {
          id: "welcome",
          sender: "ai",
          text: welcomeText,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  }, [user, primaryRole, messages.length]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = (textToSend?: string) => {
    const text = (textToSend || input).trim();
    if (!text || askMutation.isPending) return;

    const userMsg: Message = {
      id: Math.random().toString(36).substring(2),
      sender: "user",
      text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!textToSend) setInput("");
    askMutation.mutate(text);
  };

  const getRoleChips = () => {
    if (primaryRole.includes("admin")) {
      return [
        "How do access request approvals work?",
        "What are the department workflow rules?",
        "How do I index a new policy document?",
      ];
    }
    if (primaryRole.includes("manager")) {
      return [
        "What should I check before approving a claim?",
        "How do policy violation flags work?",
        "What are the approval delegation guidelines?",
      ];
    }
    return [
      "What is the maximum daily meal limit?",
      "What travel & flight expenses are covered?",
      "What receipts are required for submission?",
    ];
  };

  return (
    <>
      {/* Floating Action Button */}
      <button
        aria-label="Open AI Assistant"
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full bg-blue-600 text-white font-medium shadow-lg hover:bg-blue-700 active:scale-95 transition-all group"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <Sparkle className="w-5 h-5 animate-pulse text-amber-300" weight="fill" />
        <span className="text-sm font-semibold">{isOpen ? "Close AI Chat" : "AI Advisor"}</span>
      </button>

      {/* Chat Modal Window */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-50 w-96 max-w-[calc(100vw-2rem)] h-[540px] max-h-[80vh] flex flex-col rounded-2xl border border-slate-200 bg-white dark:bg-slate-900 dark:border-slate-800 shadow-2xl overflow-hidden transition-all animate-in fade-in slide-in-from-bottom-5 duration-200">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3.5 border-b border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-900/80 backdrop-blur-md">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400">
                <Robot className="w-5 h-5" weight="bold" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{roleTitle}</h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block animate-ping" />
                  Powered by NVIDIA NIM &amp; RAG
                </p>
              </div>
            </div>
            <button
              aria-label="Close Chat"
              className="p-1.5 rounded-lg text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
              onClick={() => setIsOpen(false)}
              type="button"
            >
              <X className="w-4 h-4" weight="bold" />
            </button>
          </div>

          {/* Messages Container */}
          <div className="flex-1 p-4 overflow-y-auto space-y-4 text-xs">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`flex gap-2.5 ${msg.sender === "user" ? "flex-row-reverse" : "flex-row"}`}
              >
                <div
                  className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                    msg.sender === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-amber-100 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400"
                  }`}
                >
                  {msg.sender === "user" ? <User className="w-4 h-4" /> : <Sparkle className="w-4 h-4" weight="fill" />}
                </div>

                <div
                  className={`max-w-[80%] rounded-2xl p-3 space-y-2 ${
                    msg.sender === "user"
                      ? "bg-blue-600 text-white rounded-tr-none"
                      : "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 rounded-tl-none border border-slate-200/50 dark:border-slate-700/50"
                  }`}
                >
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                  
                  {/* Citations */}
                  {msg.citations && msg.citations.length > 0 && (
                    <div className="pt-2 border-t border-slate-200 dark:border-slate-700/60 space-y-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1">
                        <Quotes className="w-3 h-3" /> Grounded Evidence
                      </span>
                      {msg.citations.map((c, i) => (
                        <div key={i} className="text-[11px] bg-white/60 dark:bg-slate-900/60 p-2 rounded-lg italic text-slate-600 dark:text-slate-300 border border-slate-200/40 dark:border-slate-700/40">
                          "{c.excerpt}"
                        </div>
                      ))}
                    </div>
                  )}

                  <span className="block text-[9px] opacity-60 text-right">{msg.timestamp}</span>
                </div>
              </div>
            ))}

            {askMutation.isPending && (
              <div className="flex items-center gap-2 text-slate-400 italic">
                <Robot className="w-4 h-4 animate-bounce" />
                <span>Checking grounded policy evidence…</span>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Role Suggestions */}
          <div className="px-3 py-2 border-t border-slate-100 dark:border-slate-800/60 bg-slate-50/50 dark:bg-slate-900/50 flex gap-1.5 overflow-x-auto scrollbar-none">
            {getRoleChips().map((chip) => (
              <button
                key={chip}
                type="button"
                className="whitespace-nowrap text-[11px] px-2.5 py-1 rounded-full border border-slate-200 bg-white hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 shrink-0 transition-colors"
                onClick={() => handleSend(chip)}
              >
                {chip}
              </button>
            ))}
          </div>

          {/* Input Form */}
          <form
            className="p-3 border-t border-slate-200 dark:border-slate-800 flex gap-2 items-center bg-white dark:bg-slate-900"
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
          >
            <input
              className="flex-1 text-xs px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-hidden focus:ring-2 focus:ring-blue-500"
              disabled={askMutation.isPending}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask ${roleTitle}…`}
              value={input}
            />
            <button
              aria-label="Send Message"
              className="p-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-50 transition-colors shrink-0"
              disabled={!input.trim() || askMutation.isPending}
              type="submit"
            >
              <PaperPlaneRight className="w-4 h-4" weight="bold" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
