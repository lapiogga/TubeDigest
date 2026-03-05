import { NextRequest, NextResponse } from "next/server";
import { getBackendToken, proxyToBackend } from "@/lib/backend";

export async function POST(req: NextRequest) {
  const result = await getBackendToken(req);
  if (result instanceof NextResponse) return result;

  return proxyToBackend("/api/youtube/sync-subscriptions", result.token, { method: "POST" });
}
