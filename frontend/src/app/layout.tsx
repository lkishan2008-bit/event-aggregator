import type { Metadata, Viewport } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import BottomNav from "@/components/BottomNav";
import TopNav from "@/components/TopNav";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const spaceGrotesk = Space_Grotesk({
  variable: "--font-space-grotesk",
  subsets: ["latin"],
  weight: ["500", "700"],
});

export const metadata: Metadata = {
  title: "event-aggregator",
  description: "Every student event in your city, in one feed.",
};

export const viewport: Viewport = {
  themeColor: "#1f1f2e",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${spaceGrotesk.variable} h-full antialiased`}>
      <body className="min-h-full font-sans">
        <TopNav />
        <div className="mx-auto min-h-screen w-full max-w-6xl pb-24 md:pb-12">{children}</div>
        <BottomNav />
      </body>
    </html>
  );
}