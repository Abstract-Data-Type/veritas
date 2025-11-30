import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import { header, footer, cn } from "@/lib/theme";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Veritas News - News Landscape: Left & Right",
  description: "Explore news articles across the political spectrum with AI-powered bias analysis",
};

function Header() {
  return (
    <header className={header.wrapper}>
      <div className={header.container}>
        <Link href="/" className="flex items-center gap-2">
          <span className={header.logo}>
            <span className={header.logoAccent}>Veritas</span>
            <span className={header.logoText}>News</span>
          </span>
        </Link>
        <nav className={header.nav}>
          <Link href="/" className={header.navLink}>
            Home
          </Link>
          <span className={header.navBadge}>News Bias Analysis</span>
        </nav>
      </div>
    </header>
  );
}

function Footer() {
  return (
    <footer className={footer.wrapper}>
      <div className={footer.container}>
        <p className={footer.text}>Veritas News - Understanding political bias in news coverage</p>
        <p className={footer.subtext}>Powered by AI-driven analysis</p>
      </div>
    </footer>
  );
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={cn(geistSans.variable, geistMono.variable, "antialiased")}>
        <div className="flex min-h-screen flex-col bg-white">
          <Header />
          <main className="flex-1">{children}</main>
          <Footer />
        </div>
      </body>
    </html>
  );
}
