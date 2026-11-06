import type { Metadata } from "next";
import Nav from "@/components/Nav";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL?.replace(/\/$/, "") ?? "http://localhost:3000",
  ),
  title: "ResearchFlow AI — Qatar job market intelligence",
  description:
    "Evidence-backed analysis of Qatar job ads: skills demand, qualifications, and learning recommendations with cited sources.",
  openGraph: {
    siteName: "ResearchFlow AI",
    type: "website",
  },
  twitter: {
    card: "summary",
  },
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        <Nav />
        <main>{children}</main>
        <footer className="mt-20 border-t border-line bg-white/60">
          <div className="container-page flex flex-col gap-2 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between">
            <p>
              ResearchFlow AI · Qatar job market intelligence ·{" "}
              <span className="font-mono text-xs">v0.1.0</span>
            </p>
            <p>
              Seed corpus for development ·{" "}
              <a className="underline decoration-maroon/30 underline-offset-2 hover:text-maroon" href="/about">
                methodology
              </a>
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
