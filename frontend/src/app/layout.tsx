import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { cn } from "@/lib/utils";
import Link from "next/link";
import { Camera } from "lucide-react";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });

export const metadata: Metadata = {
  title: "PhotoFlow",
  description: "AI-powered photo management and distribution",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={cn("h-full", "antialiased", "font-sans", inter.variable)}
      suppressHydrationWarning
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="container flex h-14 max-w-screen-2xl items-center px-4">
            <Link href="/" className="flex items-center space-x-2 font-bold hover:opacity-80 transition-opacity">
              <Camera className="h-6 w-6" />
              <span>PhotoFlow</span>
            </Link>
          </div>
        </header>
        <main className="flex-1 flex flex-col">{children}</main>
      </body>
    </html>
  );
}
