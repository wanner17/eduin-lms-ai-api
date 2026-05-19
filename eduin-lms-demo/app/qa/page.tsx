"use client";
import { useState, useEffect, useRef } from "react";
import { askQuestion } from "@/lib/api";
import { useMaterials } from "@/lib/useMaterials";

type Citation = { index: number; material_name: string; page: number; text: string };
type Message = { role: "user" | "assistant"; text: string; citations?: Citation[] };

export default function QAPage() {
  const { materials } = useMaterials(false);
  const [selectedCourseId, setSelectedCourseId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() =>
    typeof crypto !== "undefined" && crypto.randomUUID
      ? crypto.randomUUID()
      : Math.random().toString(36).slice(2) + Date.now().toString(36)
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const ready = materials.filter((m) => m.status === "READY");
    if (ready.length > 0 && selectedCourseId === null) {
      setSelectedCourseId(ready[0].course_id ?? null);
    }
  }, [materials]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAsk = async () => {
    if (!query.trim() || loading) return;
    const userMsg = query;
    setQuery("");
    setMessages((prev) => [...prev, { role: "user", text: userMsg }]);
    setLoading(true);
    try {
      const res = await askQuestion({
        query: userMsg,
        course_id: selectedCourseId ?? undefined,
        session_id: sessionId,
      });
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: res.answer, citations: res.citations },
      ]);
    } catch (e: unknown) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", text: `오류: ${e instanceof Error ? e.message : "알 수 없는 오류"}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const courseIds = [...new Set(materials.map((m) => m.course_id))];

  return (
    <div className="max-w-2xl mx-auto flex flex-col gap-4" style={{ height: "calc(100vh - 4rem)" }}>
      <div>
        <h2 className="text-xl font-semibold">질의응답 (QA)</h2>
        <p className="text-sm text-gray-500 mt-1">강의자료를 기반으로 AI에게 질문하세요.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <label className="text-xs font-medium text-gray-600 block mb-1.5">학습 코스</label>
        {courseIds.length === 0 ? (
          <p className="text-sm text-gray-400">업로드된 자료가 없습니다. 먼저 강의자료를 업로드하세요.</p>
        ) : (
          <select
            value={selectedCourseId ?? ""}
            onChange={(e) => setSelectedCourseId(Number(e.target.value))}
            className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {courseIds.map((id) => (
              <option key={id} value={id}>Course {id}</option>
            ))}
          </select>
        )}
      </div>

      <div className="flex-1 bg-white rounded-xl border border-gray-200 flex flex-col min-h-0">
        <div className="flex-1 overflow-auto p-4 space-y-4">
          {messages.length === 0 && (
            <p className="text-sm text-gray-400 text-center mt-8">질문을 입력하세요.</p>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm ${
                  msg.role === "user" ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-800"
                }`}
              >
                <p className="whitespace-pre-wrap">{msg.text}</p>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-200 space-y-1">
                    {msg.citations.map((c) => (
                      <p key={c.index} className="text-xs text-gray-500">
                        [{c.index}] {c.material_name} p.{c.page}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl px-4 py-2.5 text-sm text-gray-400">
                생각 중...
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="border-t border-gray-200 p-3 flex gap-2">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleAsk()}
            placeholder="질문을 입력하세요... (Enter로 전송)"
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleAsk}
            disabled={loading || !query.trim()}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-700 transition-colors"
          >
            전송
          </button>
        </div>
      </div>
    </div>
  );
}
