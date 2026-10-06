import type { Metadata, Viewport } from "next";
import { Noto_Sans_Telugu, Outfit } from "next/font/google";
import "./globals.css";
import { TopBar } from "../components/TopBar";

const outfit = Outfit({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-outfit",
  display: "swap",
});

const telugu = Noto_Sans_Telugu({
  subsets: ["telugu"],
  weight: ["400", "600", "700"],
  variable: "--font-telugu",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FixMyTown",
  description: "Hyderabad street issues within 20 km of where you are standing",
  icons: { icon: "/brand/logo.png" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${outfit.variable} ${telugu.variable}`}>
      <body>
        <TopBar />
        {children}
      </body>
    </html>
  );
}
