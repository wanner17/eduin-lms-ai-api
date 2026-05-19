"use client";
import { useState, useEffect } from "react";
import { listMaterials } from "./api";

export type MaterialRecord = {
  material_id: string;
  file_name: string;
  status: string;
  course_id?: number;
  chunk_count?: number;
  uploaded_at?: string;
};

export function useMaterials(filterReady = false) {
  const [materials, setMaterials] = useState<MaterialRecord[]>([]);

  useEffect(() => {
    // API에서 먼저 로드 (어느 기기에서 접속해도 동일)
    listMaterials()
      .then((apiList) => {
        // localStorage의 course_id 등 추가 정보와 병합
        const stored: MaterialRecord[] = JSON.parse(
          localStorage.getItem("lms_materials") ?? "[]"
        );
        const storedMap = Object.fromEntries(stored.map((m) => [m.material_id, m]));
        const merged = apiList.map((m) => ({ ...storedMap[m.material_id], ...m }));
        localStorage.setItem("lms_materials", JSON.stringify(merged));
        setMaterials(filterReady ? merged.filter((m) => m.status === "READY") : merged);
      })
      .catch(() => {
        // API 실패 시 localStorage 폴백
        const stored: MaterialRecord[] = JSON.parse(
          localStorage.getItem("lms_materials") ?? "[]"
        );
        setMaterials(filterReady ? stored.filter((m) => m.status === "READY") : stored);
      });
  }, [filterReady]);

  return { materials, setMaterials };
}
