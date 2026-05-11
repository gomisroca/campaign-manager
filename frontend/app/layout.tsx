import type { Metadata } from "next";
import { Geist } from "next/font/google";
import { Toaster } from "sileo";
import "./globals.css";
import { AuthProvider } from "@/contexts/auth";
import { OrgProvider } from "@/contexts/org";
import { ThemeProvider } from "next-themes";

const geist = Geist({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: {
    default: "Trellis",
    template: "%s | Trellis",
  },
  description: "Multi-tenant SaaS starter — built to be extended and shipped.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={geist.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <AuthProvider>
            <OrgProvider>
              {children}
              <Toaster position="bottom-right" />
            </OrgProvider>
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
