"use client";
import { useState, useCallback } from "react";
import { uploadMaterial, getMaterialStatus } from "@/lib/api";
import { useMaterials, type MaterialRecord } from "@/lib/useMaterials";

const STATUS_COLORS: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-700",
  PROCESSING: "bg-blue-100 text-blue-700",
  READY: "bg-green-100 text-green-700",
  FAILED: "bg-red-100 text-red-700",
};

export default function IngestPage() {
  const { materials, setMaterials } = useMaterials(false);
  const [file, setFile] = useState<File | null>(null);
  const [courseId, setCourseId] = useState("1");
  const [lectureId, setLectureId] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [dragging, setDragging] = useState(false);

  const pollStatus = useCallback((material_id: string) => {
    const interval = setInterval(async () => {
      try {
        const status = await getMaterialStatus(material_id);
        setMaterials((prev) => {
          const updated = prev.map((m) =>
            m.material_id === material_id
              ? { ...m, status: status.status, chunk_count: status.chunk_count }
              : m
          );
          localStorage.setItem("lms_materials", JSON.stringify(updated));
          return updated;
        });
        if (status.status === "READY" || status.status === "FAILED") {
          clearInterval(interval);
        }
      } catch {
        clearInterval(interval);
      }
    }, 2000);
  }, [setMaterials]);

  const handleUpload = async () => {
    if (!file || !courseId) return;
    setError("");
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("course_id", courseId);
      if (lectureId) formData.append("lecture_id", lectureId);

      const res = await uploadMaterial(formData);
      const record: MaterialRecord = {
        material_id: res.material_id,
        file_name: res.file_name,
        course_id: parseInt(courseId),
        status: "PENDING",
        uploaded_at: new Date().toISOString(),
      };
      const updated = [record, ...materials];
      setMaterials(updated);
      localStorage.setItem("lms_materials", JSON.stringify(updated));
      setFile(null);
      pollStatus(res.material_id);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "업로드 실패");
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <div>
        <h2 className="text-xl font-semibold">강의자료 업로드</h2>
        <p className="text-sm text-gray-500 mt-1">
          PDF, PPTX, DOCX 파일을 업로드하면 AI가 자동으로 학습합니다.
        </p>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => document.getElementById("fileInput")?.click()}
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 hover:border-gray-400"
          }`}
        >
          <input
            id="fileInput"
            type="file"
            accept=".pdf,.pptx,.docx"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
          {file ? (
            <p className="text-sm font-medium text-blue-600">{file.name}</p>
          ) : (
            <>
              <p className="text-sm text-gray-500">파일을 끌어다 놓거나 클릭해서 선택</p>
              <p className="text-xs text-gray-400 mt-1">PDF · PPTX · DOCX</p>
            </>
          )}
        </div>

        <div className="flex gap-3">
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-600 mb-1">Course ID *</label>
            <input
              type="number"
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="1"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs font-medium text-gray-600 mb-1">Lecture ID (선택)</label>
            <input
              type="number"
              value={lectureId}
              onChange={(e) => setLectureId(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="없음"
            />
          </div>
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          onClick={handleUpload}
          disabled={!file || !courseId || uploading}
          className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-medium disabled:opacity-50 hover:bg-blue-700 transition-colors"
        >
          {uploading ? "업로드 중..." : "업로드 시작"}
        </button>
      </div>

      {materials.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">업로드된 자료</h3>
          {materials.map((m) => (
            <div
              key={m.material_id}
              className="bg-white rounded-lg border border-gray-200 px-4 py-3 flex items-center justify-between gap-3"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">{m.file_name}</p>
                <p className="text-xs text-gray-400 font-mono">{m.material_id}</p>
                <p className="text-xs text-gray-400">
                  Course {m.course_id}
                  {m.uploaded_at ? ` · ${new Date(m.uploaded_at).toLocaleString("ko-KR")}` : ""}
                  {m.chunk_count ? ` · ${m.chunk_count}개 청크` : ""}
                </p>
              </div>
              <span
                className={`shrink-0 px-2.5 py-1 rounded-full text-xs font-medium ${
                  STATUS_COLORS[m.status] ?? "bg-gray-100 text-gray-700"
                }`}
              >
                {m.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
