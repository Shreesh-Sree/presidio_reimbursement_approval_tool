import { useState, useRef, useEffect } from "react";
import { Sparkle, X, PaperPlaneRight, Robot, User, Quotes } from "@phosphor-icons/react";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "../../auth/AuthContext";
import { aiChatApi, type AIChatResponse } from "../../lib/api";

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
  const roleTitle =
    primaryRole === "admin" || primaryRole === "administrator"
      ? "Admin AI Advisor"
      : primaryRole === "manager"
        ? "Manager AI Compliance"
        : "Employee AI Assistant";

  const askMutation = useMutation({
    mutationFn: (questionText: string) => aiChatApi.ask(questionText),
    onSuccess: (data: AIChatResponse) => {
      const aiMsg: Message = {
        id: crypto.randomUUID(),
        sender: "ai",
        text: data.answer,
        citations: data.citations?.length ? data.citations : undefined,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, aiMsg]);
    },
    onError: (err: Error) => {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: "ai",
          text: err.message || "Something went wrong. Please try again.",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    },
  });

  useEffect(() => {
    if (messages.length === 0 && user) {
      let welcomeText =
        "Hello! I'm your AI Expense & Policy Assistant. Ask me anything about claiming expenses, travel caps, or receipt requirements.";
      if (primaryRole.includes("admin")) {
        welcomeText =
          "Hello Admin! I'm your System & Policy AI Advisor. Ask me about workflows, access approvals, or policy document management.";
      } else if (primaryRole.includes("manager")) {
        welcomeText =
          "Hello Manager! I'm your AI Compliance Advisor. Ask me about approval checks, policy flags, or delegation rules.";
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

    setMessages((prev) => [
      ...prev,
      {
        id: crypto.randomUUID(),
        sender: "user",
        text,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
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
        "What should I check before approving?",
        "How do policy violation flags work?",
        "What are the delegation guidelines?",
      ];
    }
    return [
      "What is the maximum daily meal limit?",
      "What travel expenses are covered?",
      "What receipts are required?",
    ];
  };

  return (
    <>
      {/* Floating Action Button */}
      <button
        aria-label="Open AI Assistant"
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-full bg-[#00ED64] text-[#001E2B] font-medium shadow-lg hover:bg-[#00C956] active:scale-95 transition-all group"
        onClick={() => setIsOpen(!isOpen)}
        type="button"
      >
        <Sparkle className="w-5 h-5 animate-pulse text-[#001E2B]" weight="fill" />
        <span className="text-sm font-semibold">{isOpen ? "Close AI Chat" : "AI Advisor"}</span>
      </button>

      {/* Chat Modal Window */}
      {isOpen && (
        <div className="fixed bottom-20 right-6 z-50 w-96 max-w-[calc(100vw-2rem)] h-[540px] max-h-[80vh] flex flex-col rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] dark:bg-[#001E2B] dark:border-[rgba(255,255,255,0.1)] shadow-2xl overflow-hidden transition-all">
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3.5 border-b border-[var(--color-hairline)] dark:border-[rgba(255,255,255,0.1)] bg-[var(--color-surface)] dark:bg-[#0D2B36] backdrop-blur-md">
            <div className="flex items-center gap-2.5">
              <div className="p-2 rounded-lg bg-[#E3FCF7] dark:bg-[rgba(0,237,100,0.1)] text-[#00684A] dark:text-[#00ED64]">
                <Robot className="w-5 h-5" weight="bold" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{roleTitle}</h3>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 flex items-center gap-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 inline-block" />
                  Powered by NVIDIA NIM &amp; RAG
                </p>
              </div>
            </div>
            <button
              aria-label="Close Chat"
              className="p-1.5 rounded-lg text-[var(--color-slate)] hover:bg-[var(--color-surface)] dark:hover:bg-[#00384D] transition-colors"
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
                      ? "bg-[#001E2B] text-[#00ED64]"
                      : "bg-amber-100 dark:bg-amber-950/40 text-amber-600 dark:text-amber-400"
                  }`}
                >
                  {msg.sender === "user" ? (
                    <User className="w-4 h-4" />
                  ) : (
                    <Sparkle className="w-4 h-4" weight="fill" />
                  )}
                </div>

                <div
                  className={`max-w-[80%] rounded-2xl p-3 space-y-2 ${
                    msg.sender === "user"
                      ? "bg-[#001E2B] text-white rounded-tr-none"
                      : "bg-[var(--color-surface)] dark:bg-[#0D2B36] text-[var(--color-ink)] rounded-tl-none border border-[var(--color-hairline)] dark:border-[rgba(255,255,255,0.08)]"
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
                        <div
                          key={i}
                          className="text-[11px] bg-white/60 dark:bg-slate-900/60 p-2 rounded-lg italic text-slate-600 dark:text-slate-300 border border-slate-200/40 dark:border-slate-700/40"
                        >
                          &ldquo;{c.excerpt}&rdquo;
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
                <span>Thinking…</span>
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
              className="flex-1 text-xs px-3 py-2 rounded-lg border border-[var(--color-hairline-strong)] dark:border-[rgba(255,255,255,0.16)] bg-[var(--color-surface)] dark:bg-[#0D2B36] text-[var(--color-ink)] focus:outline-hidden focus:ring-2 focus:ring-[#00ED64]"
              disabled={askMutation.isPending}
              onChange={(e) => setInput(e.target.value)}
              placeholder={`Ask ${roleTitle}…`}
              value={input}
            />
            <button
              aria-label="Send Message"
              className="p-2 rounded-lg bg-[#00ED64] hover:bg-[#00C956] text-[#001E2B] disabled:opacity-50 transition-colors shrink-0"
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
