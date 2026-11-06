import Link from "next/link";

const stack = [
  ["Web", "Next.js 15 App Router, React 19, Tailwind CSS"],
  ["API", "FastAPI, Pydantic v2, SQLAlchemy 2 (async)"],
  ["Data", "PostgreSQL 16; Postgres-backed queue with SKIP LOCKED"],
  ["Models", "Gemini Flash-Lite for extraction, Flash for narrative; deterministic fallback"],
  ["Hosting", "Vercel Hobby + Supabase Free + Oracle Cloud Always Free (ARM)"],
];

const pipeline = [
  {
    step: "Collect",
    body: "Seeded, robots-aware collection. Every source has a policy status, attribution flag, crawl delay, and a recorded fetch. Live adapters parse JSON-LD JobPosting data first.",
  },
  {
    step: "De-duplicate",
    body: "URLs are canonicalized (tracking parameters removed) and clustered by a title, company, and description fingerprint before extraction.",
  },
  {
    step: "Extract",
    body: "Each ad becomes structured requirements: skills, required versus preferred, degree, certifications, experience, and language. Every field carries a verbatim evidence quote.",
  },
  {
    step: "Analyze",
    body: "SQL computes counts and percentages into an evidence pack. Claims cite an evidence ID, and evidence IDs map back to actual job records and source URLs.",
  },
  {
    step: "Validate",
    body: "A deterministic validator rejects narrative claims with unknown references or numbers that are not present in the evidence pack. The template report is the fallback.",
  },
];

const policy = [
  "Only public pages that are permitted by robots.txt and the source's terms are collected.",
  "No login walls, paywalls, CAPTCHA bypassing, or personal data. Protected attributes are flagged and excluded from requirements.",
  "Each source records its robots URL, terms URL, policy status, attribution requirement, and crawl delay.",
  "The MVP ships with a clearly labeled sample corpus. It is not presented as live Qatar market coverage.",
  "Reports state snapshot versus trend limits, salary coverage, source diversity, and language coverage.",
];

export default function AboutPage() {
  return (
    <div className="container-page py-12">
      <div className="mx-auto max-w-4xl">
        <p className="text-xs font-semibold uppercase tracking-wide text-maroon">Methodology</p>
        <h1 className="mt-3 text-4xl font-black tracking-tight text-ink">
          Evidence first, narrative second
        </h1>
        <p className="mt-4 max-w-3xl text-lg leading-8 text-muted">
          ResearchFlow AI answers a simple question: what does the Qatari job market actually ask
          for? It is designed so that every number in a report can be traced to an ad, and every
          recommendation can be traced to a number.
        </p>

        <section className="card mt-10 p-6 sm:p-8">
          <h2 className="section-title">Pipeline</h2>
          <ol className="mt-5 space-y-5">
            {pipeline.map((item, index) => (
              <li key={item.step} className="flex gap-4">
                <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-maroon/10 font-mono text-xs font-bold text-maroon">
                  {String(index + 1).padStart(2, "0")}
                </span>
                <div>
                  <h3 className="font-semibold text-ink">{item.step}</h3>
                  <p className="mt-1 text-sm leading-6 text-muted">{item.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <section className="card p-6">
            <h2 className="section-title">Architecture</h2>
            <dl className="mt-4 space-y-3 text-sm">
              {stack.map(([label, value]) => (
                <div key={label}>
                  <dt className="text-xs font-semibold uppercase tracking-wide text-muted">
                    {label}
                  </dt>
                  <dd className="mt-0.5 leading-6 text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          </section>

          <section className="card p-6">
            <h2 className="section-title">Data-source policy</h2>
            <ul className="mt-4 space-y-3 text-sm leading-6 text-muted">
              {policy.map((item) => (
                <li key={item} className="flex gap-2">
                  <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-maroon/50" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>

        <section className="card mt-6 p-6 sm:p-8">
          <h2 className="section-title">Evaluation</h2>
          <div className="mt-4 grid gap-5 sm:grid-cols-3">
            <div>
              <p className="text-sm font-semibold text-ink">Extraction quality</p>
              <p className="mt-1 text-sm leading-6 text-muted">
                Precision and recall against a hand-labeled ad set, tracked per skill category and
                per required/preferred label.
              </p>
            </div>
            <div>
              <p className="text-sm font-semibold text-ink">Evidence validity</p>
              <p className="mt-1 text-sm leading-6 text-muted">
                Share of extracted items whose quote appears verbatim in the ad. The target is
                100%; anything lower is surfaced, not hidden.
              </p>
            </div>
            <div>
              <p className="text-sm font-semibold text-ink">Claim faithfulness</p>
              <p className="mt-1 text-sm leading-6 text-muted">
                Every report claim is checked against the evidence pack. Unsupported claims are
                rejected and replaced by the deterministic template.
              </p>
            </div>
          </div>
        </section>

        <section className="card mt-6 p-6 sm:p-8">
          <h2 className="section-title">Known limitations</h2>
          <ul className="mt-4 space-y-3 text-sm leading-6 text-muted">
            <li>
              <span className="font-semibold text-ink">The demo corpus is seeded.</span> Ads are
              sample fixtures written for development. They are not a live census of Qatar
              vacancies.
            </li>
            <li>
              <span className="font-semibold text-ink">Snapshot, not trend.</span> A single
              collection wave cannot support “demand is rising” claims. Trends require repeat
              sampling over time.
            </li>
            <li>
              <span className="font-semibold text-ink">English extraction only.</span> Arabic ads
              are detected but Arabic requirement extraction is a later phase. The UI stays English.
            </li>
            <li>
              <span className="font-semibold text-ink">Salary is mostly absent.</span> When salary
              coverage is low, compensation is not analyzed and the report says so.
            </li>
            <li>
              <span className="font-semibold text-ink">No authentication in the MVP.</span> Runs and
              reports are public and rate limits are coarse. Production would add per-IP quotas and
              abuse controls.
            </li>
          </ul>
        </section>

        <section className="card mt-6 bg-maroon p-6 text-white sm:p-8">
          <h2 className="text-lg font-semibold">Cost model</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-white/80">
            The stack is designed to stay at $0: Vercel Hobby for the frontend, Supabase Free for
            Postgres, Oracle Cloud Always Free for the worker, Gemini free tier for extraction and
            narrative, and a deterministic path when the model is unavailable.
          </p>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link
              href="/"
              className="rounded-xl bg-white px-4 py-2.5 text-sm font-semibold text-maroon"
            >
              Generate a report
            </Link>
            <Link
              href="/jobs"
              className="rounded-xl border border-white/30 px-4 py-2.5 text-sm font-semibold text-white"
            >
              Browse the corpus
            </Link>
          </div>
        </section>
      </div>
    </div>
  );
}
