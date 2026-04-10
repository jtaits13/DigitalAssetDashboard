const ITEMS = [
  {
    title: "Tokenized liquidity: weekly institutional flows",
    summary: "Cross-chain settlement volumes rose as treasury desks rotated into short-duration cash equivalents.",
    date: "Apr 2, 2026",
  },
  {
    title: "Digital assets custody: operational resilience checklist",
    summary: "Key controls for key management, disaster recovery, and third-party attestations in 2026.",
    date: "Mar 28, 2026",
  },
  {
    title: "On-chain FX and stablecoin usage in wholesale payments",
    summary: "How correspondent-style messaging maps to programmable settlement windows on public networks.",
    date: "Mar 21, 2026",
  },
];

export function NewsSection() {
  return (
    <section className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-lg shadow-black/20">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-zinc-500">News</h2>
      <ul className="mt-4 space-y-5">
        {ITEMS.map((item) => (
          <li key={item.title} className="border-b border-[var(--border)] pb-5 last:border-0 last:pb-0">
            <p className="text-xs text-zinc-500">{item.date}</p>
            <h3 className="mt-1 font-medium text-zinc-100">{item.title}</h3>
            <p className="mt-2 text-sm leading-relaxed text-zinc-400">{item.summary}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
