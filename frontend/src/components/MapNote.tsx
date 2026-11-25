"use client";

import { useLocale } from "@/lib/i18n";

/** Standard cartographic disclaimer. Health authorities require one next to every map. */
export default function MapNote() {
  const { locale } = useLocale();
  return (
    <p className="map-note small muted">
      {locale === "fa"
        ? "مرزها و نام‌ها تقریبی‌اند (داده‌ی ساده‌شده‌ی Natural Earth) و بیانگر هیچ دیدگاهی درباره‌ی وضعیت حقوقی کشور، سرزمین یا منطقه نیستند. مرزهای مورد مناقشه نشان داده نمی‌شوند و کشورهای کوچک ممکن است دیده نشوند؛ از فهرست استفاده کنید."
        : "Boundaries and names are approximate (simplified Natural Earth data) and imply no opinion on the legal status of any country, territory or area. Disputed borders are not drawn and small countries may be invisible; use the list."}
    </p>
  );
}
