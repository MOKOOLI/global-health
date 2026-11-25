"use client";

import { useLocale } from "@/lib/i18n";

// Placeholders in [brackets] must be filled by the operator before launch.
const REPO = "https://github.com/MOKOOLI";
const C = {
  fa: {
    title: "اعتماد، حریم خصوصی و شرایط استفاده",
    note: "این صفحه یادداشت کاری اپراتور است و مشاوره‌ی حقوقی نیست. بخش‌های داخل [کروشه] باید پیش از انتشار عمومی تکمیل شوند.",
    s: [
      ["شرایط استفاده", ["داده‌ها فقط برای اطلاع‌رسانی اپیدمیولوژیک‌اند، نه تشخیص یا تصمیم درمانی. هر عدد با منبع، مجوز و نوع داده (گزارش‌شده، برآورد، مدل‌سازی، ساختگی) نمایش داده می‌شود.",
        "سیگنال‌های هشدار زودهنگام تحلیل آماریِ شمارش‌های گزارش‌شده‌اند، نه اعلام رسمی WHO یا هیچ مرجع دیگر و نه پیش‌بینی پاندمی‌ی نوپدید.",
        "داده‌ی هر منبع تابع مجوز همان منبع است (صفحه‌ی «داده و مجوزها»). فهرست مجوزها هنوز با شرایط فعلی ارائه‌دهندگان تطبیق داده نشده است.",
        "سرویس بدون ضمانت ارائه می‌شود؛ مسئولیت کاربرد بالینی با کاربر است."]],
      ["حریم خصوصی", ["حساب کاربری، کوکی تبلیغاتی و ابزار ردیابی نداریم.",
        "پرسش‌های «پرسش هوشمند» برای پاسخ به سرور ما فرستاده می‌شود و در پایگاه داده ذخیره نمی‌شود، اما لاگ‌های سرویس‌دهنده‌ی میزبان (مثلاً Vercel یا Render) ممکن است نشانی URL شامل متن پرسش و نشانی IP را نگه دارند. اطلاعات بیمار را در جست‌وجو وارد نکنید.",
        "محدودکننده‌ی نرخ، IP را فقط در حافظه (یا در Redis در صورت پیکربندی) و حداکثر چند دقیقه نگه می‌دارد.",
        "ورودی صوتی از Web Speech API مرورگر شما استفاده می‌کند؛ بسته به مرورگر ممکن است صدا برای تبدیل به متن به شرکت سازنده‌ی مرورگر برود. می‌توانید به‌جای آن تایپ کنید.",
        "فایل CSV در «ابزارها» فقط در مرورگر شما خوانده می‌شود. مرورگر فقط ترجیح «حالت سبک» را در localStorage نگه می‌دارد."]],
      ["دسترس‌پذیری", ["هدف: WCAG 2.2 سطح AA. نقشه‌ها جایگزین متنی دارند، تمام کنترل‌ها با صفحه‌کلید قابل‌استفاده‌اند و انیمیشن با تنظیم «کاهش حرکت» متوقف می‌شود.",
        "ما هنوز ممیزی مستقل دسترس‌پذیری یا تست با صفحه‌خوان انجام نداده‌ایم. مشکلات را گزارش کنید."]],
      ["عدالت داده و محدودیت‌ها", ["کشورها با ظرفیت ثبت و گزارش ضعیف‌تر ممکن است «کم‌شمار» به نظر برسند، نه واقعاً کم‌بیمار. نبودن داده یعنی نبودن گزارش.",
        "بسیاری از اعداد برآوردهای مدل‌اند (مثلاً GBD) و بازه‌ی عدم‌قطعیت دارند؛ مقایسه‌ی کشورها بدون استانداردسازی سنی گمراه‌کننده است (ابزار ASR).",
        "انگلیس، اسکاتلند و… جدا نیستند؛ داده در سطح بریتانیا است. داده‌ی زیرملی هنوز وجود ندارد."]],
      ["گزارش خطا", [`اگر عددی نادرست یا قدیمی دیدید، در GitHub یک Issue بسازید (${REPO}) و نشانی صفحه، شاخص و سال را بنویسید. خطاهای داده را در اولویت بررسی می‌کنیم.`]],
      ["راهبری و تماس", ["[نام و وابستگی اپراتور/مسئول محتوا]", "[ایمیل تماس]", "[هیئت مشورتی علمی: هنوز تشکیل نشده است]"]],
    ],
  },
  en: {
    title: "Trust, privacy and terms",
    note: "This page is the operator's working draft, not legal advice. Items in [brackets] must be completed before public launch.",
    s: [
      ["Terms of use", ["The data are for epidemiological information only, not diagnosis or treatment decisions. Every number shows its source, licence and data type (reported, estimated, modeled, synthetic).",
        "Early-warning signals are statistical analyses of reported counts. They are not an official declaration by WHO or any authority, and not a prediction of a novel pandemic.",
        "Each source's data stay under that source's licence (see Data & licences). The register has not yet been verified against providers' current terms.",
        "The service is provided without warranty; responsibility for any clinical use rests with the user."]],
      ["Privacy", ["No accounts, advertising cookies or tracking tools.",
        "Questions typed into Ask are sent to our server to be answered and are not stored in the database, but the hosting provider's logs (e.g. Vercel or Render) may keep the request URL, which contains the question text, and your IP address. Do not enter patient information.",
        "The rate limiter keeps your IP only in memory (or in Redis if configured) for a few minutes.",
        "Voice input uses your browser's Web Speech API; depending on the browser, audio may be sent to the browser vendor for transcription. You can type instead.",
        "The CSV viewer in Tools reads the file in your browser only. The only thing stored is your Lite-mode preference, in localStorage."]],
      ["Accessibility", ["Target: WCAG 2.2 AA. Maps have text alternatives, controls work with a keyboard, and animation stops under “reduce motion”.",
        "We have not yet had an independent accessibility audit or screen-reader testing. Please report problems."]],
      ["Data equity and limits", ["Countries with weaker registration and reporting can look “low burden” when they are only low-reporting. No data means no report.",
        "Many numbers are model estimates (e.g. GBD) with uncertainty intervals; comparing countries without age standardisation misleads (see the ASR tool).",
        "England, Scotland and so on are not separate; data are at UK level. There is no subnational data yet."]],
      ["Report an error", [`If a number looks wrong or outdated, open an issue on GitHub (${REPO}) with the page, indicator and year. Data errors get priority.`]],
      ["Governance and contact", ["[Operator name and affiliation / content owner]", "[Contact email]", "[Scientific advisory board: not yet formed]"]],
    ],
  },
};

export default function Trust() {
  const { locale } = useLocale();
  const c = C[locale === "fa" ? "fa" : "en"];
  return (
    <div className="shell page prose">
      <h1>{c.title}</h1>
      <p className="warn-box">{c.note}</p>
      {c.s.map(([h, items]) => (
        <section key={h as string}>
          <h2>{h as string}</h2>
          <ul>{(items as string[]).map((x, i) => <li key={i}>{x}</li>)}</ul>
        </section>
      ))}
    </div>
  );
}
