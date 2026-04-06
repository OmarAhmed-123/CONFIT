import { z } from "zod";
import { NextRequest, NextResponse } from "next/server";
import { proxyToAuthUpstream } from "@/server/auth/upstream";

const revokeSchema = z.object({ sessionId: z.string().min(1) });

export async function POST(req: NextRequest) {
  const body = await req.json().catch(() => null);
  const parsed = revokeSchema.safeParse(body);
  if (!parsed.success) {
    return NextResponse.json({ error: "VALIDATION_ERROR" }, { status: 400 });
  }
  return proxyToAuthUpstream(req, "/api/auth/sessions/revoke", { method: "POST", body: parsed.data });
}
