import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = { title: "AI Agent Studio", description: "Local-first multi-agent workspace" };
export default function RootLayout({children}:{children:React.ReactNode}) {
 return <html lang="ar" dir="rtl"><body>{children}</body></html>;
}
