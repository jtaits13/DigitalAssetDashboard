import { getStablecoinVolumeSeries, type VolumeRange } from "@/lib/rwa";
import { NextResponse } from "next/server";

const RANGES: VolumeRange[] = ["1m", "3m", "6m", "1y", "5y"];

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const raw = (searchParams.get("range") ?? "1m") as VolumeRange;
  const range = RANGES.includes(raw) ? raw : "1m";
  const data = await getStablecoinVolumeSeries(process.env.RWA_API_KEY, range);
  return NextResponse.json({ range, ...data });
}
