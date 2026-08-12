import Link from "next/link";
import type { ReactNode } from "react";

type SiteSection = "history" | "how-it-works" | "about";

export default function SiteHeader({
  active,
  actions,
}: {
  active?: SiteSection;
  actions?: ReactNode;
}) {
  const link = (section: SiteSection, label: string) => (
    <Link href={`/${section}`} aria-current={active === section ? "page" : undefined}>
      {label}
    </Link>
  );

  return (
    <header className="header">
      <Link className="wordmark" href="/" aria-label="DeepScout home">DeepScout</Link>
      <div className="header-right">
        <nav className="nav" aria-label="Primary navigation">
          {link("history", "History")}
          {link("how-it-works", "How it works")}
          {link("about", "About")}
        </nav>
        {actions && <div className="header-actions">{actions}</div>}
      </div>
    </header>
  );
}
