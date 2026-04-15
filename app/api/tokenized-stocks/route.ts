import { getTokenizedStocksData } from "@/lib/tokenizedStocks";
import { NextResponse } from "next/server";

export async function GET() {
  const data = await getTokenizedStocksData();
  return NextResponse.json(data);
}
