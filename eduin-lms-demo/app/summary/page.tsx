"use client";
import { useState, useEffect } from "react";
import { generateSummary } from "@/lib/api";
import { useMaterials } from "@/lib/useMaterials";

type MaterialRecord = { material_id: string; file_name: string; status: string };
type OverviewResult = {
  title: string;
  summary: string;
  sections: { heading: string; points: string[] }[];
  key_concepts: string[];
};
type KeywordsResult = {
  keywords: { term: string; definition: string; importance: string; source_page: number }[];
};
type FlashcardResult = {
  flashcards: { front: string; back: string; hint?: string; source_page: number }[];
};

const IMPORTANCE_COLORS: Record<string, string> = {
  high: "bg-red-50 text-red-600",
  medium: "bg-yellow-50 text-yellow-700",
  low: "bg-gray-50 text-gray-500",
};

const TABS = [
  { value: "overview", label: "핵심 요약" },
  { value: "keywords", label: "키워드" },
  { value: "flashcard", label: "플래시카드" },
];

export default function SummaryPage() {
  const { materials } = useMaterials(true);
  const [selectedId, setSelectedId] = useState("");
  const [summaryType, setSummaryType] = useState("overview");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [flipped, setFlipped] = useState<Record<number, boolean>>({});

  useEffect(() => {
    if (materials.length > 0 && !selectedId) setSelectedId(materials[0].material_id);
  }, [materials]);

  const handleGenerate = async () => {
    if (!selectedId) return;
    setError("");
    setResult(null);
    setFlipped({});
    setLoading(true);
    try {
      const res = await generateSummary({ material_id: selectedId, summary_type: summaryType });
      setResult(res.result);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "요약 생성 실패");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold">요약 자료</h2>
        <p className="text-sm text-gray-500 mt-1">강의자료를 AI가 요약·정리합니다.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1.5">강의자료</label>
          {materials.length === 0 ? (
            <p className="text-sm text-gray-400">READY 상태의 자료가 없습니다.</p>
          ) : (
            <select
              value={selectedId}
              onChange={(e) => setSelectedId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {materials.map((m) => (
                <option key={m.material_id} value={m.material_id}>{m.file_name}</option>
              ))}
            </select>
          )}
        </div>

        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {TABS.map((tab) => (
            <button
              key={tab.value}
              onClick={() => setSummaryType(tab.value)}
              className={`flex-1 py-1.5 rounded-md text-sm font-medium transition-colors ${
                summaryType === tab.value
                  ? "bg-white text-gray-900 shadow-sm"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={handleGenerate}
          disabled={loading || !selectedId}
          className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-700 transition-colors"
        >
          {loading ? "생성 중..." : "요약 생성"}
        </button>
      </div>

      {result && summaryType === "overview" && (() => {
        const r = result as unknown as OverviewResult;
        return (
          <div className="space-y-4">
            {r.title && <h3 className="text-lg font-semibold">{r.title}</h3>}
            {r.summary && (
              <div className="bg-blue-50 border border-blue-100 rounded-xl p-4 text-sm text-blue-900 leading-relaxed">
                {r.summary}
              </div>
            )}
            {r.sections?.map((s, i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-xl p-4">
                <h4 className="font-medium text-sm mb-2">{s.heading}</h4>
                <ul className="space-y-1">
                  {s.points?.map((p, j) => (
                    <li key={j} className="text-sm text-gray-600 flex gap-2">
                      <span className="text-blue-400 mt-0.5 shrink-0">•</span>
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {r.key_concepts && r.key_concepts.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">핵심 개념</p>
                <div className="flex flex-wrap gap-2">
                  {r.key_concepts.map((c, i) => (
                    <span key={i} className="px-2.5 py-1 bg-gray-100 text-gray-700 rounded-full text-xs">
                      {c}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        );
      })()}

      {result && summaryType === "keywords" && (() => {
        const r = result as unknown as KeywordsResult;
        return (
          <div className="space-y-2">
            {r.keywords?.map((kw, i) => (
              <div key={i} className="bg-white border border-gray-200 rounded-xl p-4">
                <div className="flex items-start justify-between gap-2 mb-1">
                  <h4 className="font-medium text-sm">{kw.term}</h4>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        IMPORTANCE_COLORS[kw.importance] ?? "bg-gray-50 text-gray-500"
                      }`}
                    >
                      {kw.importance}
                    </span>
                    <span className="text-xs text-gray-400">p.{kw.source_page}</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600">{kw.definition}</p>
              </div>
            ))}
          </div>
        );
      })()}

      {result && summaryType === "flashcard" && (() => {
        const r = result as unknown as FlashcardResult;
        return (
          <div className="grid gap-3">
            {r.flashcards?.map((fc, i) => (
              <div
                key={i}
                onClick={() => setFlipped((prev) => ({ ...prev, [i]: !prev[i] }))}
                className="bg-white border border-gray-200 rounded-xl p-5 cursor-pointer hover:border-blue-300 transition-colors min-h-[90px] flex flex-col justify-center"
              >
                {flipped[i] ? (
                  <div>
                    <p className="text-xs font-medium text-green-600 mb-1.5">정답</p>
                    <p className="text-sm font-medium">{fc.back}</p>
                    {fc.hint && <p className="text-xs text-gray-400 mt-1">{fc.hint}</p>}
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-medium">{fc.front}</p>
                    <p className="text-xs text-gray-400 mt-1.5">탭하면 답이 보입니다</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        );
      })()}
    </div>
  );
}
