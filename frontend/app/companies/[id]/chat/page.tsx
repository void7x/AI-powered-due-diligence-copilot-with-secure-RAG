"use client";

import { useEffect, useRef, useState } from "react";
import { Send } from "lucide-react";
import { Badge, Button, Card, Input } from "@/components/ui";
import { ChatMessageView } from "@/components/ChatMessage";
import { SourcePanel } from "@/components/SourcePanel";
import { useApiData } from "@/hooks/useApi";
import { apiPost } from "@/lib/api";
import type { ChatAnswer, ChatMessageItem, Citation } from "@/types";

const SUGGESTIONS = [
  "What are the biggest financial risks?",
  "How is revenue growing?",
  "Is the company financially healthy?",
  "What are the biggest opportunities?",
  "What changed this year?",
  "What should I ask management?",
];

export default function ChatPage({ params }: { params: { id: string } }) {
  const companyId = params.id;
  const { data: history } = useApiData<ChatMessageItem[]>(`/api/companies/${companyId}/chat/messages`);
  const [messages, setMessages] = useState<ChatMessageItem[]>([]);
  const [citations, setCitations] = useState<Record<string, Citation[]>>({});
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (history && messages.length === 0 && history.length > 0) {
      setMessages(history);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [history]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, busy]);

  const ask = async (question: string) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    const userMsg: ChatMessageItem = {
      id: `tmp-${Date.now()}`, role: "user", content: q, meta: {}, created_at: new Date().toISOString(),
    };
    setMessages((m) => [...m, userMsg]);
    try {
      const answer = await apiPost<ChatAnswer>(`/api/companies/${companyId}/chat`, {
        question: q, session_id: sessionId,
      });
      setSessionId(answer.session_id);
      const assistantMsg: ChatMessageItem = {
        id: answer.message_id, role: "assistant", content: answer.answer,
        meta: { confidence: answer.confidence, claims: answer.claims,
                insufficient_evidence: answer.insufficient_evidence, provider: answer.provider },
        created_at: new Date().toISOString(),
      };
      setCitations((c) => ({ ...c, [answer.message_id]: answer.citations }));
      setMessages((m) => [...m, assistantMsg]);
    } catch (e) {
      setMessages((m) => [...m, {
        id: `err-${Date.now()}`, role: "assistant", content:
          e instanceof Error ? `Error: ${e.message}` : "Something went wrong.",
        meta: {}, created_at: new Date().toISOString(),
      }]);
    } finally {
      setBusy(false);
    }
  };

  const lastAnswerId = [...messages].reverse().find((m) => m.role === "assistant" && citations[m.id])?.id;

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_300px]">
      <Card className="flex h-[calc(100vh-220px)] min-h-[480px] flex-col">
        <div className="border-b border-slate-100 px-5 py-3">
          <h2 className="text-sm font-semibold text-slate-900">Due-diligence Copilot</h2>
          <p className="text-xs text-slate-500">Evidence-backed answers with clickable citations</p>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {messages.length === 0 && (
            <div className="py-6 text-center">
              <p className="text-sm font-medium text-slate-600">Ask anything about this company.</p>
              <p className="mt-1 text-xs text-slate-400">Answers are grounded in the processed documents; the copilot states when evidence is insufficient.</p>
              <div className="mt-4 flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button key={s} onClick={() => ask(s)}
                    className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs text-slate-600 transition hover:border-navy-300 hover:bg-navy-50 hover:text-navy-700">
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <ChatMessageView key={m.id} message={m} companyId={companyId} citations={citations[m.id]} />
          ))}
          {busy && (
            <div className="flex items-center gap-2 text-xs text-slate-400" role="status">
              <span className="flex gap-1">
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:0ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:150ms]" />
                <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:300ms]" />
              </span>
              Retrieving evidence and drafting an answer…
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <form className="flex items-center gap-2 border-t border-slate-100 px-4 py-3"
              onSubmit={(e) => { e.preventDefault(); ask(input); }}>
          <Input value={input} onChange={(e) => setInput(e.target.value)}
                 placeholder="Ask a question, e.g. “What are the biggest risks?”"
                 aria-label="Your question" maxLength={2000} disabled={busy} />
          <Button type="submit" disabled={busy || input.trim().length < 2} aria-label="Send">
            <Send size={14} />
          </Button>
        </form>
      </Card>

      <div className="space-y-4">
        <Card className="p-4">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">How answers work</h3>
          <ol className="mt-2 space-y-1.5 text-[11px] leading-relaxed text-slate-500">
            <li>1. Your question is embedded and matched against this company&apos;s document chunks.</li>
            <li>2. Hybrid retrieval blends vector similarity, keyword relevance and source priority.</li>
            <li>3. Evidence ids (SOURCE_N) are assigned by the backend — the model can only cite what was retrieved.</li>
            <li>4. Every claim is typed: fact, analysis, recommendation or uncertainty.</li>
          </ol>
        </Card>
        {lastAnswerId && <SourcePanel citations={citations[lastAnswerId] ?? []} companyId={companyId} />}
        {!lastAnswerId && (
          <Card className="p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suggested questions</h3>
            <div className="mt-2 flex flex-col gap-1.5">
              {SUGGESTIONS.map((s) => (
                <button key={s} onClick={() => ask(s)}
                  className="rounded-md border border-slate-200 px-2.5 py-1.5 text-left text-xs text-slate-600 transition hover:border-navy-300 hover:bg-navy-50">
                  {s}
                </button>
              ))}
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}
