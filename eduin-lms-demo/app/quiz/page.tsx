"use client";
import { useState, useEffect } from "react";
import { generateQuiz } from "@/lib/api";
import { useMaterials, type MaterialRecord } from "@/lib/useMaterials";
type QuizItem = {
  quiz_type: string;
  question: string;
  options?: Record<string, string>;
  answer: string;
  explanation: string;
  keywords: string[];
  source_page: number;
};

const QUIZ_TYPES = [
  { value: "mcq", label: "객관식" },
  { value: "ox", label: "OX" },
  { value: "short", label: "단답형" },
  { value: "essay", label: "서술형" },
];
const DIFFICULTIES = ["easy", "medium", "hard"];
const DIFFICULTY_KO: Record<string, string> = { easy: "쉬움", medium: "보통", hard: "어려움" };

export default function QuizPage() {
  const { materials } = useMaterials(true);
  const [selectedId, setSelectedId] = useState("");
  const [quizTypes, setQuizTypes] = useState(["mcq"]);
  const [count, setCount] = useState(5);
  const [difficulty, setDifficulty] = useState("medium");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [quizzes, setQuizzes] = useState<QuizItem[]>([]);
  const [currentIdx, setCurrentIdx] = useState(0);
  const [userAnswers, setUserAnswers] = useState<Record<number, string>>({});
  const [revealed, setRevealed] = useState<Record<number, boolean>>({});
  const [mode, setMode] = useState<"config" | "quiz" | "done">("config");

  useEffect(() => {
    if (materials.length > 0 && !selectedId) setSelectedId(materials[0].material_id);
  }, [materials]);

  const toggleType = (t: string) =>
    setQuizTypes((prev) => (prev.includes(t) ? prev.filter((x) => x !== t) : [...prev, t]));

  const handleGenerate = async () => {
    if (!selectedId || quizTypes.length === 0) return;
    setError("");
    setLoading(true);
    try {
      const res = await generateQuiz({ material_id: selectedId, quiz_types: quizTypes, count, difficulty });
      setQuizzes(res.quizzes);
      setCurrentIdx(0);
      setUserAnswers({});
      setRevealed({});
      setMode("quiz");
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "문제 생성 실패");
    } finally {
      setLoading(false);
    }
  };

  const q = quizzes[currentIdx];
  const isLast = currentIdx === quizzes.length - 1;
  const score = quizzes.filter((q, i) => {
    const ua = (userAnswers[i] ?? "").trim().toUpperCase();
    return ua === (q.answer ?? "").trim().toUpperCase();
  }).length;

  if (mode === "done") {
    return (
      <div className="max-w-xl mx-auto">
        <div className="bg-white rounded-xl border border-gray-200 p-10 text-center space-y-4">
          <div className="text-5xl">🎉</div>
          <h2 className="text-xl font-semibold">퀴즈 완료!</h2>
          <p className="text-4xl font-bold text-blue-600">{score} / {quizzes.length}</p>
          <p className="text-sm text-gray-500">
            {score === quizzes.length ? "완벽합니다!" : score >= quizzes.length / 2 ? "잘 하셨어요!" : "다시 한 번 도전해보세요!"}
          </p>
          <button
            onClick={() => setMode("config")}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            다시 생성
          </button>
        </div>
      </div>
    );
  }

  if (mode === "quiz" && q) {
    const isRevealed = revealed[currentIdx];
    const userAns = userAnswers[currentIdx] ?? "";
    const isCorrect = userAns.trim().toUpperCase() === (q.answer ?? "").trim().toUpperCase();

    return (
      <div className="max-w-xl mx-auto space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">문제 풀기</h2>
          <span className="text-sm text-gray-500">{currentIdx + 1} / {quizzes.length}</span>
        </div>

        <div className="w-full bg-gray-200 rounded-full h-1.5">
          <div
            className="bg-blue-600 h-1.5 rounded-full transition-all"
            style={{ width: `${(currentIdx / quizzes.length) * 100}%` }}
          />
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
          <div className="flex gap-2">
            <span className="px-2 py-0.5 bg-blue-50 text-blue-600 rounded text-xs font-medium">
              {q.quiz_type.toUpperCase()}
            </span>
            <span className="px-2 py-0.5 bg-gray-50 text-gray-500 rounded text-xs">
              p.{q.source_page}
            </span>
          </div>

          <p className="text-sm font-medium leading-relaxed">{q.question}</p>

          {q.quiz_type === "mcq" && q.options && (
            <div className="space-y-2">
              {Object.entries(q.options).map(([key, val]) => {
                let cls = "border border-gray-200 hover:border-blue-300 hover:bg-blue-50";
                if (isRevealed) {
                  if (key === q.answer) cls = "border-green-500 bg-green-50";
                  else if (key === userAns) cls = "border-red-400 bg-red-50";
                } else if (key === userAns) {
                  cls = "border-blue-500 bg-blue-50";
                }
                return (
                  <button
                    key={key}
                    disabled={isRevealed}
                    onClick={() => setUserAnswers((prev) => ({ ...prev, [currentIdx]: key }))}
                    className={`w-full text-left px-4 py-2.5 rounded-lg text-sm transition-colors ${cls}`}
                  >
                    <span className="font-medium">{key}.</span> {val}
                  </button>
                );
              })}
            </div>
          )}

          {q.quiz_type === "ox" && (
            <div className="flex gap-3">
              {["O", "X"].map((opt) => {
                let cls = "flex-1 border border-gray-200 hover:border-blue-300 hover:bg-blue-50";
                if (isRevealed) {
                  if (opt === q.answer) cls = "flex-1 border-green-500 bg-green-50";
                  else if (opt === userAns) cls = "flex-1 border-red-400 bg-red-50";
                } else if (opt === userAns) {
                  cls = "flex-1 border-blue-500 bg-blue-50";
                }
                return (
                  <button
                    key={opt}
                    disabled={isRevealed}
                    onClick={() => setUserAnswers((prev) => ({ ...prev, [currentIdx]: opt }))}
                    className={`${cls} py-4 rounded-lg text-2xl font-bold transition-colors`}
                  >
                    {opt}
                  </button>
                );
              })}
            </div>
          )}

          {(q.quiz_type === "short" || q.quiz_type === "essay") && (
            <textarea
              value={userAns}
              onChange={(e) => setUserAnswers((prev) => ({ ...prev, [currentIdx]: e.target.value }))}
              disabled={isRevealed}
              rows={q.quiz_type === "essay" ? 4 : 2}
              placeholder="답을 입력하세요..."
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none disabled:bg-gray-50"
            />
          )}

          {isRevealed && (
            <div
              className={`rounded-lg p-3 text-sm space-y-1 ${
                isCorrect ? "bg-green-50 border border-green-200" : "bg-amber-50 border border-amber-200"
              }`}
            >
              <p className="font-medium">{isCorrect ? "✓ 정답!" : "✗ 오답"}</p>
              <p><span className="font-medium">정답:</span> {q.answer}</p>
              {q.explanation && <p className="text-gray-600 mt-1">{q.explanation}</p>}
            </div>
          )}

          <div className="flex gap-2 pt-1">
            {!isRevealed && (
              <button
                onClick={() => setRevealed((prev) => ({ ...prev, [currentIdx]: true }))}
                className="flex-1 border border-gray-300 py-2 rounded-lg text-sm hover:bg-gray-50 transition-colors"
              >
                정답 확인
              </button>
            )}
            {(isRevealed || q.quiz_type === "essay") && (
              <button
                onClick={() => (isLast ? setMode("done") : setCurrentIdx((i) => i + 1))}
                className="flex-1 bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
              >
                {isLast ? "결과 보기" : "다음 문제"}
              </button>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold">문제 생성</h2>
        <p className="text-sm text-gray-500 mt-1">AI가 강의자료를 기반으로 문제를 자동 생성합니다.</p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1.5">강의자료 선택</label>
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

        <div>
          <label className="text-xs font-medium text-gray-600 block mb-1.5">문제 유형</label>
          <div className="flex gap-2 flex-wrap">
            {QUIZ_TYPES.map(({ value, label }) => (
              <button
                key={value}
                onClick={() => toggleType(value)}
                className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
                  quizTypes.includes(value)
                    ? "bg-blue-600 text-white border-blue-600"
                    : "border-gray-300 text-gray-600 hover:border-gray-400"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-5 items-start">
          <div className="flex-1">
            <label className="text-xs font-medium text-gray-600 block mb-1.5">문제 수: {count}개</label>
            <input
              type="range"
              min={1}
              max={20}
              value={count}
              onChange={(e) => setCount(Number(e.target.value))}
              className="w-full"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600 block mb-1.5">난이도</label>
            <div className="flex gap-1">
              {DIFFICULTIES.map((d) => (
                <button
                  key={d}
                  onClick={() => setDifficulty(d)}
                  className={`px-3 py-1.5 rounded-lg text-xs border transition-colors ${
                    difficulty === d
                      ? "bg-blue-600 text-white border-blue-600"
                      : "border-gray-300 text-gray-600 hover:border-gray-400"
                  }`}
                >
                  {DIFFICULTY_KO[d]}
                </button>
              ))}
            </div>
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={handleGenerate}
          disabled={loading || !selectedId || quizTypes.length === 0}
          className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-700 transition-colors"
        >
          {loading ? "생성 중..." : `문제 ${count}개 생성`}
        </button>
      </div>
    </div>
  );
}
