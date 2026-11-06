import Link from "next/link";

const links = [
  { href: "/", label: "Search" },
  { href: "/jobs", label: "Jobs" },
  { href: "/about", label: "Methodology" },
];

export default function Nav() {
  return (
    <nav className="sticky top-0 z-40 border-b border-line/80 bg-[#fbf8f3]/90 backdrop-blur">
      <div className="container-page flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-3">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-maroon text-sm font-black text-white">
            RF
          </span>
          <span className="flex flex-col leading-tight">
            <span className="text-sm font-bold tracking-tight text-ink">ResearchFlow AI</span>
            <span className="text-[11px] text-muted">Qatar market intelligence</span>
          </span>
        </Link>
        <div className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-muted transition hover:bg-sand hover:text-ink"
            >
              {link.label}
            </Link>
          ))}
          <a
            href="https://github.com/yazan-alsaleh/ResearchFlow_AI"
            target="_blank"
            rel="noreferrer"
            className="ml-1 hidden rounded-lg border border-line px-3 py-2 text-sm font-semibold text-ink transition hover:border-maroon/30 hover:text-maroon sm:inline-flex"
          >
            GitHub
          </a>
        </div>
      </div>
    </nav>
  );
}
