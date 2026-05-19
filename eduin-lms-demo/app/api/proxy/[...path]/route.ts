import { NextRequest, NextResponse } from "next/server";

const API_BASE = process.env.LMS_API_URL ?? "http://localhost:8000";
const API_KEY = process.env.LMS_API_KEY ?? "dev-secret-key";

async function handler(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  const { path } = await params;
  const targetUrl = `${API_BASE}/api/v1/${path.join("/")}`;

  const headers = new Headers();
  headers.set("x-api-key", API_KEY);
  const contentType = req.headers.get("content-type") ?? "";
  if (contentType) headers.set("content-type", contentType);

  let body: ArrayBuffer | undefined;
  if (req.method !== "GET" && req.method !== "HEAD") {
    body = await req.arrayBuffer();
  }

  try {
    const res = await fetch(targetUrl, { method: req.method, headers, body });
    const data = await res.arrayBuffer();
    return new NextResponse(data, {
      status: res.status,
      headers: { "content-type": res.headers.get("content-type") ?? "application/json" },
    });
  } catch {
    return NextResponse.json({ error: "API 서버에 연결할 수 없습니다" }, { status: 503 });
  }
}

export const GET = handler;
export const POST = handler;
export const DELETE = handler;
