import { NextRequest, NextResponse } from "next/server";
import { getBackendToken, proxyToBackend } from "@/lib/backend";

export async function GET(req: NextRequest) {
  const result = await getBackendToken(req);
  if (result instanceof NextResponse) return result;

  const searchParams = req.nextUrl.searchParams;
  return proxyToBackend("/api/youtube/subscriptions", result.token, { searchParams });
}
