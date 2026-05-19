const BASE = "/api/proxy";

export async function uploadMaterial(formData: FormData) {
  const res = await fetch(`${BASE}/ingest/materials`, { method: "POST", body: formData });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getMaterialStatus(materialId: string) {
  const res = await fetch(`${BASE}/ingest/materials/${materialId}/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function listMaterials() {
  const res = await fetch(`${BASE}/ingest/materials`);
  if (!res.ok) throw new Error(await res.text());
  return res.json() as Promise<{ material_id: string; file_name: string; status: string; chunk_count?: number }[]>;
}

export async function askQuestion(body: {
  query: string;
  course_id?: number;
  session_id?: string;
}) {
  const res = await fetch(`${BASE}/qa/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateQuiz(body: {
  material_id: string;
  course_id?: number;
  quiz_types: string[];
  count: number;
  difficulty: string;
}) {
  const res = await fetch(`${BASE}/quiz/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function generateSummary(body: {
  material_id: string;
  course_id?: number;
  summary_type: string;
}) {
  const res = await fetch(`${BASE}/summary/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
