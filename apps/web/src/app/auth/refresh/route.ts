import { NextRequest } from "next/server";
import { proxyToAuthUpstream } from "@/server/auth/upstream";

export async function POST(req: NextRequest) {
  return proxyToAuthUpstream(req, "/api/auth/refresh", { method: "POST" });
}
