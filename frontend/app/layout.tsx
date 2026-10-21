import "@fontsource-variable/inter";
import "./globals.css";
import type { ReactNode } from "react";
import Gate from "@/components/Gate";

export const metadata = { title: "StockAI - Volatility Intelligence" };

const THEME_INIT = `try{var t=localStorage.getItem('theme');if(!t){t=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light'}document.documentElement.classList.toggle('dark',t==='dark')}catch(e){}`;

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: THEME_INIT }} /></head>
      <body className="font-sans">{children}<Gate /></body>
    </html>
  );
}
