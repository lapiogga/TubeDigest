import { NextRequest, NextResponse } from "next/server";
import { getBackendToken, proxyToBackend } from "@/lib/backend";

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ channel_id: string }> }
) {
  const result = await getBackendToken(req);
  if (result instanceof NextResponse) return result;

  const { channel_id } = await params;
  return proxyToBackend(`/api/youtube/subscriptions/${channel_id}`, result.token, { method: "DELETE" });
}
