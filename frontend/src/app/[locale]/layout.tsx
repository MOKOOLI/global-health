import "@fontsource-variable/vazirmatn";
import "../globals.css";
import type { Metadata } from "next";
import Chrome from "@/components/Chrome";
import { LocaleProvider } from "@/lib/i18n";
import type { Locale } from "@/lib/types";

export const dynamicParams = false;

export function generateStaticParams() {
  return [{ locale: "fa" }, { locale: "en" }];
}

export const metadata: Metadata = {
  title: "Global Health Atlas · اطلس سلامت جهانی",
  description: "Open disease statistics for every country, for clinicians.",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg" },
};

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const { locale } = await params;
  const loc = (locale === "en" ? "en" : "fa") as Locale;
  return (
    <html lang={loc} dir={loc === "fa" ? "rtl" : "ltr"}>
      <body>
        <LocaleProvider locale={loc}>
          <Chrome>{children}</Chrome>
        </LocaleProvider>
      </body>
    </html>
  );
}
