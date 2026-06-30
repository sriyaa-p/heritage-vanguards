import type { Metadata } from "next";
import "./globals.css";
import Header from "@/components/Header";

export const metadata: Metadata = {
  title: "Heritage Sentinel AI",
  description: "Multi-agent system for UNESCO heritage site review",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50 text-gray-900 min-h-screen flex flex-col">
        <Header />
        <div className="flex-1">
          {children}
        </div>
      </body>
    </html>
  );
}
