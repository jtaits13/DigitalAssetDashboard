import { getTopIssuers } from "@/lib/rwa";
import { NextResponse } from "next/server";

export async function GET() {
  const issuers = await getTopIssuers(process.env.RWA_API_KEY);
  return NextResponse.json({ issuers });
}
