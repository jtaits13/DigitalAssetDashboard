import { getStablecoinSummary } from "@/lib/rwa";
import { NextResponse } from "next/server";

export async function GET() {
  const data = await getStablecoinSummary(process.env.RWA_API_KEY);
  return NextResponse.json(data);
}
