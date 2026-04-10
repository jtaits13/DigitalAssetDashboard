/**
 * Spot crypto ETP / ETF trusts — edit CIKs to match your coverage list.
 * Ticker + CIK pair is used to resolve the SEC filing index (same approach as ETF-Dashboard).
 */
export type CryptoEtpFund = {
  name: string;
  ticker: string;
  /** SEC Central Index Key, digits (leading zeros optional) */
  cik: string;
};

/**
 * Seed list (CIKs from common ETF trust shells; verify tickers vs your prospectus).
 * Add/remove rows to mirror your “Crypto ETPs” table.
 */
export const CRYPTO_ETP_FUNDS: CryptoEtpFund[] = [
  { name: "iShares Bitcoin Trust", ticker: "IBIT", cik: "0001100663" },
  { name: "Fidelity Wise Origin Bitcoin Fund", ticker: "FBTC", cik: "0000315066" },
  { name: "ARK 21Shares Bitcoin ETF", ticker: "ARKB", cik: "0001579982" },
  { name: "Invesco Galaxy Bitcoin ETF", ticker: "BTCO", cik: "0001333493" },
  { name: "VanEck Bitcoin Trust", ticker: "HODL", cik: "0001137360" },
];
