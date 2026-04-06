import { NextRequest } from "next/server";
import { proxyToAuthUpstream } from "@/server/auth/upstream";

export async function GET(req: NextRequest) {
  return proxyToAuthUpstream(req, "/api/auth/me", { method: "GET" });
}
