import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import AuthGuard from "@/components/AuthGuard";

export const metadata: Metadata = {
  title: "Candidate Practice Portal",
  description: "AI-powered practice interview platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="bg-slate-900 text-zinc-100 min-h-screen flex h-full">
        <AuthGuard>
          <Sidebar />
          <main className="flex-1 overflow-auto">{children}</main>
        </AuthGuard>
      </body>
    </html>
  );
}
