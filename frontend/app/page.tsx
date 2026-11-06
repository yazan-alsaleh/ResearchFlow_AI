import Link from "next/link";
import SearchBox from "@/components/SearchBox";
import CoverageStats from "@/components/CoverageStats";

const outcomes = [
  {
    title: "Required vs preferred",
    body: "Every ad is split into must-have and nice-to-have skills, with a verbatim quote behind each extraction.",
  },
  {
    title: "Demand, not vibes",
    body: "Counts and percentages are computed in SQL. The language model writes the narrative, not the numbers.",
  },
  {
    title: "Cited conclusions",
    body: "Each claim references an evidence ID, and each evidence ID maps to real job cards and source links.",
  },
  {
    title: "All job families",
    body: "AI, finance, civil engineering, marketing, healthcare, HR, education, logistics, legal, and more.",
  },
];

const steps = [
  {
    number: "01",
    title: "Collect",
    body: "Robots-aware collection from permitted sources, URL canonicalization, and near-duplicate clustering.",
  },
  {
    number: "02",
    title: "Extract",
    body: "Structured requirements with evidence quotes, canonical skill normalization, and a deterministic fallback.",
  },
  {
    number: "03",
    title: "Analyze",
    body: "SQL aggregation produces an evidence pack. The Intelligence Analyst writes a grounded report and a validator checks every claim.",
  },
];

export default function HomePage() {
  return (
    <div>
      <section className="subtle-grid border-b border-line">
        <div className="container-page grid gap-10 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:items-center lg:py-24">
          <div>
            <span className="badge border-maroon/20 bg-maroon/5 text-maroon">
              Qatar · evidence-backed
            </span>
            <h1 className="mt-5 max-w-2xl text-4xl font-black tracking-tight text-ink sm:text-5xl">
              What does the Qatari job market actually ask for?
            </h1>
            <p className="mt-5 max-w-xl text-lg leading-8 text-muted">
              Enter any job title. ResearchFlow AI collects relevant Qatar job ads, extracts
              requirements, and generates a market report where every conclusion cites evidence.
            </p>
            <div className="mt-6 flex flex-wrap gap-3 text-sm text-muted">
              <span className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5">
                <span className="h-2 w-2 rounded-full bg-emerald-500" />
                Deterministic analytics
              </span>
              <span className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5">
                <span className="h-2 w-2 rounded-full bg-maroon" />
                LLM narrative + validator
              </span>
              <span className="inline-flex items-center gap-2 rounded-full border border-line bg-white px-3 py-1.5">
                <span className="h-2 w-2 rounded-full bg-amber-500" />
                Free-tier deployable
              </span>
            </div>
          </div>
          <SearchBox />
        </div>
      </section>

      <section className="container-page py-10">
        <CoverageStats />
      </section>

      <section className="container-page py-12">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-maroon">What you get</p>
            <h2 className="mt-2 text-2xl font-bold tracking-tight text-ink">
              A report you can defend in an interview
            </h2>
          </div>
          <Link href="/about" className="btn-secondary">
            Read the methodology
          </Link>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {outcomes.map((item) => (
            <article key={item.title} className="card p-6">
              <h3 className="font-semibold text-ink">{item.title}</h3>
              <p className="mt-2 text-sm leading-6 text-muted">{item.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-line bg-white/60">
        <div className="container-page py-12">
          <p className="text-xs font-semibold uppercase tracking-wide text-maroon">How it works</p>
          <h2 className="mt-2 text-2xl font-bold tracking-tight text-ink">
            Three bounded agents, one deterministic pipeline
          </h2>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            {steps.map((step) => (
              <article key={step.number} className="rounded-2xl border border-line bg-white p-6">
                <span className="font-mono text-xs font-bold text-maroon">{step.number}</span>
                <h3 className="mt-3 font-semibold text-ink">{step.title}</h3>
                <p className="mt-2 text-sm leading-6 text-muted">{step.body}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="container-page py-16">
        <div className="card overflow-hidden">
          <div className="grid gap-8 p-8 md:grid-cols-[1fr_auto] md:items-center">
            <div>
              <h2 className="text-2xl font-bold tracking-tight text-ink">
                Try a title outside tech
              </h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                The corpus is intentionally cross-sector: accountant, civil engineer, nurse,
                teacher, HR specialist, marketing manager, project manager, and more. The point is
                to show the pipeline generalizes, not just to AI roles.
              </p>
            </div>
            <Link href="/jobs" className="btn-primary">
              Browse the corpus
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
