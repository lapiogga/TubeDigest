/**
 * Next.js API Route → FastAPI 프록시 공통 헬퍼
 * backendToken은 서버 사이드에서만 사용 (클라이언트 미노출)
 */
import { getToken } from "next-auth/jwt";
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** JWT 토큰에서 backendToken 추출. 없으면 401 Response 반환. */
export async function getBackendToken(
  req: NextRequest
): Promise<{ token: string } | NextResponse> {
  const jwtToken = await getToken({
    req,
    secret: process.env.NEXTAUTH_SECRET,
  });

  if (!jwtToken?.backendToken) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  return { token: jwtToken.backendToken as string };
}

/** FastAPI로 프록시 요청. backendToken을 Bearer 헤더로 전송. */
export async function proxyToBackend(
  path: string,
  backendToken: string,
  options: { method?: string; searchParams?: URLSearchParams } = {}
): Promise<NextResponse> {
  const url = new URL(path, BACKEND_URL);
  if (options.searchParams) {
    options.searchParams.forEach((value, key) => url.searchParams.set(key, value));
  }

  const res = await fetch(url.toString(), {
    method: options.method ?? "GET",
    headers: {
      Authorization: `Bearer ${backendToken}`,
      "Content-Type": "application/json",
    },
  });

  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
