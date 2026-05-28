"use client";

import { useState } from "react";
import { MessageSquare, Send } from "lucide-react";
import { Button } from "@/components/ui/button";
import { askQuestion } from "@/lib/api";

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

export function AskData({ companyId }: Props) {
  const [input, setInput]       = useState("");
  const [history, setHistory]   = useState<Turn[]>([]);
  const [busy, setBusy]         = useState(false);

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;

    setBusy(true);
    setInput("");
    setHistory((h) => [...h, { question: q, answer: null }]);

    const answer = await askQuestion(companyId, q);

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

  return (
    <div className="border rounded-xl overflow-hidden shadow-sm">
      <div className="px-4 py-3 border-b flex items-center gap-2">
        <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
        <span className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          Ask your data
        </span>
      </div>

      {/* Conversation */}
      {history.length > 0 && (
        <div className="px-4 py-3 space-y-4 max-h-[420px] overflow-y-auto">
          {history.map((turn, i) => (
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
          ))}
        </div>
      )}

      {/* Suggestion chips — only show when no conversation yet */}
      {history.length === 0 && (
        <div className="px-4 py-3 flex flex-wrap gap-2 border-b">
          {SUGGESTIONS.map((s) => (
            <button
              key={s}
              onClick={() => send(s)}
              className="text-xs px-2.5 py-1 rounded-full border hover:bg-muted/60 transition-colors text-muted-foreground hover:text-foreground"
              disabled={busy}
            >
              {s}
            </button>
          ))}
        </div>
      )}

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
          placeholder="Ask anything about your finances…"
          className="flex-1 bg-transparent text-sm px-2 py-1.5 focus:outline-none placeholder:text-muted-foreground/70"
          disabled={busy}
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
  );
}
