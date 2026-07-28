import type { Metadata } from "next";
import { Cormorant_Garamond, Manrope } from "next/font/google";
import { Nav } from "@/components/site/Nav";
import { ThemeProvider } from "@/components/site/ThemeProvider";
import { TripProvider } from "@/components/site/TripProvider";
import "./globals.css";

const sans = Manrope({
  variable: "--font-manrope",
  subsets: ["latin"],
});

const serif = Cormorant_Garamond({
  variable: "--font-cormorant",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: "Our Italy Escape",
  description: "A private, editable journey through Sardinia, Tuscany and Amalfi.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning className={`${sans.variable} ${serif.variable}`}>
      <body>
        <ThemeProvider>
          <TripProvider>
            <Nav />
            {children}
          </TripProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
