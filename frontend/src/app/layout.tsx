import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Job Scheduler | Dilamme",
  description: "HNG Stage 9 Background Job Scheduler",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <nav>
          <Link href="/" className="brand">Dilamme Scheduler</Link>
          <Link href="/">Dashboard</Link>
          <Link href="/jobs">Jobs</Link>
          <Link href="/create">Create Job</Link>
          <Link href="/dlq">DLQ</Link>
        </nav>
        <main className="container">{children}</main>
      </body>
    </html>
  );
}
