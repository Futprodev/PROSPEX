"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Send, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { askQuestion, type ChatHistoryEntry } from "@/lib/api";

interface Props {
  companyId: string;
}

interface Turn {
  question: string;
  answer:   string | null; // null while pending
}

const SUGGESTIONS = [
  "How long does my cash last?",
  "Which dimension is dragging the score down?",
  "What regulatory action is urgent this month?",
  "Where is most of my expense going?",
];

const STORAGE_PREFIX = "prospex_chat_";
const storageKey = (companyId: string) => `${STORAGE_PREFIX}${companyId}`;

function readTurns(companyId: string): Turn[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(storageKey(companyId));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as { turns: Turn[] };
    return parsed.turns ?? [];
  } catch {
    return [];
  }
}

function writeTurns(companyId: string, turns: Turn[]) {
  if (typeof window === "undefined") return;
  try {
    if (turns.length === 0) {
      localStorage.removeItem(storageKey(companyId));
    } else {
      localStorage.setItem(storageKey(companyId), JSON.stringify({ turns }));
    }
  } catch {
    // localStorage might be unavailable (private mode, quota); silently drop
  }
}

export function AgentChat({ companyId }: Props) {
  const [open, setOpen]       = useState(false);
  const [input, setInput]     = useState("");
  const [history, setHistory] = useState<Turn[]>([]);
  const [busy, setBusy]       = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Hydrate from localStorage on mount — guarded so it doesn't write to
  // storage during the initial render before we've loaded.
  useEffect(() => {
    setHistory(readTurns(companyId));
    setHydrated(true);
  }, [companyId]);

  // Persist on every change after hydration
  useEffect(() => {
    if (!hydrated) return;
    writeTurns(companyId, history);
  }, [history, companyId, hydrated]);

  // Auto-scroll to the newest turn when panel is open
  useEffect(() => {
    if (open && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [open, history]);

  // Close panel on Escape
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;

    setBusy(true);
    setInput("");
    setHistory((h) => [...h, { question: q, answer: null }]);

    // Flatten completed turns into role/content pairs so the LLM can see
    // the prior conversation and follow up correctly on pronouns ("it",
    // "that"), references ("the third one"), and elaboration requests.
    const apiHistory: ChatHistoryEntry[] = [];
    for (const turn of history) {
      apiHistory.push({ role: "user",      content: turn.question });
      if (turn.answer) {
        apiHistory.push({ role: "assistant", content: turn.answer });
      }
    }

    const answer = await askQuestion(companyId, q, apiHistory);

    setHistory((h) => {
      const copy = [...h];
      copy[copy.length - 1] = {
        question: q,
        answer:   answer ?? "Sorry — the assistant couldn't be reached.",
      };
      return copy;
    });
    setBusy(false);
  }

  function clearConversation() {
    setHistory([]);
  }

  return (
    <>
      {/* Floating launcher — visible whenever the panel is closed */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="no-print fixed bottom-6 right-6 z-40 flex items-center gap-2 px-4 py-3 rounded-full bg-foreground text-background shadow-lg hover:bg-sky-600 hover:text-white hover:shadow-xl hover:scale-105 transition-all duration-200"
          aria-label="Open chat with your data"
        >
          <Bot className="h-4 w-4" />
          <span className="text-sm font-medium">Ask your data</span>
          {history.length > 0 && (
            <span className="ml-1 inline-flex items-center justify-center min-w-[18px] h-[18px] text-[10px] font-semibold rounded-full bg-background text-foreground px-1">
              {history.length}
            </span>
          )}
        </button>
      )}

      {/* Chat panel */}
      {open && (
        <div className="no-print fixed bottom-6 right-6 z-50 w-[min(420px,calc(100vw-2rem))] max-h-[min(640px,calc(100vh-3rem))] flex flex-col border rounded-xl shadow-2xl bg-background animate-in slide-in-from-bottom-4 fade-in duration-200">

          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b">
            <div className="flex items-center gap-2">
              <Bot className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-semibold">Ask your data</span>
              {history.length > 0 && (
                <span className="text-xs text-muted-foreground">
                  · {history.length} {history.length === 1 ? "turn" : "turns"}
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              {history.length > 0 && (
                <button
                  onClick={clearConversation}
                  className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted/60 rounded-md transition-colors"
                  title="Clear conversation"
                  aria-label="Clear conversation"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              )}
              <button
                onClick={() => setOpen(false)}
                className="p-1.5 text-muted-foreground hover:text-foreground hover:bg-muted/60 rounded-md transition-colors"
                title="Close"
                aria-label="Close"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>

          {/* Conversation */}
          <div
            ref={scrollRef}
            className="flex-1 overflow-y-auto px-4 py-4 space-y-4"
          >
            {history.length === 0 ? (
              <div className="text-center space-y-3 py-6">
                <p className="text-sm text-muted-foreground">
                  Ask anything about your finances or recent briefing.
                </p>
                <div className="flex flex-wrap gap-2 justify-center">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      disabled={busy}
                      className="text-xs px-2.5 py-1 rounded-full border hover:bg-muted/60 transition-colors text-muted-foreground hover:text-foreground"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              history.map((turn, i) => (
                <div key={i} className="space-y-2">
                  <p className="text-sm font-medium">{turn.question}</p>
                  <div className="text-sm text-muted-foreground whitespace-pre-wrap pl-3 border-l-2 border-sky-200 dark:border-sky-900">
                    {turn.answer === null ? (
                      <span className="inline-flex items-center gap-2">
                        <span className="inline-block animate-spin">⟳</span>
                        Thinking…
                      </span>
                    ) : (
                      turn.answer
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Input */}
          <form
            onSubmit={(e) => {
              e.preventDefault();
              send(input);
            }}
            className="flex items-center gap-2 px-3 py-2 border-t"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type a question…"
              className="flex-1 bg-transparent text-sm px-2 py-1.5 focus:outline-none placeholder:text-muted-foreground/70"
              disabled={busy}
              autoFocus
            />
            <Button
              type="submit"
              size="sm"
              variant="ghost"
              disabled={busy || !input.trim()}
            >
              <Send className="h-3.5 w-3.5" />
            </Button>
          </form>
        </div>
      )}
    </>
  );
}
