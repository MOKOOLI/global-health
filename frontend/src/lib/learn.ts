export type Bi = { fa: string; en: string };

export interface Term { id: string; term: Bi; def: Bi; group: "burden" | "outbreak" | "data" }

export const TERMS: Term[] = [
  { id: "incidence", group: "burden", term: { fa: "بروز (Incidence)", en: "Incidence" },
    def: { fa: "تعداد موارد جدید در یک بازه‌ی زمانی (مثلاً یک سال)، معمولاً به‌صورت نرخ بر ۱۰۰ هزار نفر. نشان می‌دهد بیماری با چه سرعتی تازه رخ می‌دهد.",
           en: "New cases arising in a period (for example one year), usually as a rate per 100,000 people. It shows how fast the disease is newly occurring." } },
  { id: "prevalence", group: "burden", term: { fa: "شیوع (Prevalence)", en: "Prevalence" },
    def: { fa: "نسبت افرادی که در یک لحظه یا یک بازه بیماری را دارند (هم موارد قدیمی و هم جدید). برای بیماری‌های مزمن مهم‌تر از بروز است.",
           en: "The share of people who have the disease at a point or period in time, old and new cases together. More informative than incidence for chronic disease." } },
  { id: "mortality", group: "burden", term: { fa: "مرگ‌ومیر (Mortality)", en: "Mortality rate" },
    def: { fa: "تعداد مرگ‌های ناشی از یک بیماری نسبت به کل جمعیت (نه فقط بیماران)، معمولاً بر ۱۰۰ هزار نفر.",
           en: "Deaths from a disease relative to the whole population (not only patients), usually per 100,000." } },
  { id: "cfr", group: "burden", term: { fa: "نسبت کشندگی (CFR)", en: "Case fatality ratio (CFR)" },
    def: { fa: "نسبت مرگ‌ها به موارد تأییدشده. اگر آزمایش‌ها کم باشد یا موارد خفیف شمرده نشوند، CFR بزرگ‌تر از واقعیت دیده می‌شود. با IFR (کشندگی در همه‌ی عفونت‌ها) یکی نیست.",
           en: "Deaths divided by confirmed cases. When testing is limited and mild cases are missed, CFR looks higher than reality. It is not the same as IFR (fatality among all infections)." } },
  { id: "asr", group: "burden", term: { fa: "نرخ استانداردشده‌ی سنی", en: "Age-standardised rate" },
    def: { fa: "نرخی که اثر تفاوت ساختار سنی کشورها را حذف می‌کند تا مقایسه‌ی کشور جوان با کشور سالخورده منصفانه باشد.",
           en: "A rate adjusted for differences in age structure, so a young and an old country can be compared fairly." } },
  { id: "daly", group: "burden", term: { fa: "DALY", en: "DALY" },
    def: { fa: "سال‌های زندگی از دست‌رفته به‌خاطر مرگ زودرس (YLL) به‌علاوه‌ی سال‌های زندگی با ناتوانی (YLD). یک واحد بار بیماری برای مقایسه‌ی بیماری‌های مختلف.",
           en: "Years of life lost to premature death (YLL) plus years lived with disability (YLD): one unit of disease burden for comparing different diseases." } },
  { id: "endemic", group: "outbreak", term: { fa: "اندمیک", en: "Endemic" },
    def: { fa: "حضور مداوم و قابل‌انتظار یک بیماری در یک منطقه، با سطحی که معمولاً در همان منطقه دیده می‌شود (ممکن است فصلی نوسان کند).",
           en: "A disease that is constantly present at a level usually seen in that area (it may still vary with the seasons)." } },
  { id: "epidemic", group: "outbreak", term: { fa: "اپیدمی", en: "Epidemic / outbreak" },
    def: { fa: "افزایش موارد بیش از حد معمول و انتظار برای آن مکان و زمان. در این سایت «سیگنال بالاتر از حد انتظار» یعنی همین، اما اعلام رسمی نیست.",
           en: "Cases clearly above what is expected for that place and time. On this site an “above expected” signal means this, but it is not an official declaration." } },
  { id: "pandemic", group: "outbreak", term: { fa: "پاندمی", en: "Pandemic" },
    def: { fa: "اپیدمی که در چندین کشور یا قاره گسترش یافته و شمار زیادی از مردم را درگیر می‌کند. اعلام آن با WHO است. سایت فقط «الگوی شبه‌پاندمیک» را نشان می‌دهد.",
           en: "An epidemic spread over several countries or continents affecting many people. Naming it is WHO's call. This site only shows a “pandemic-like pattern”." } },
  { id: "pheic", group: "outbreak", term: { fa: "PHEIC", en: "PHEIC" },
    def: { fa: "«وضعیت اضطراری بهداشت عمومی با نگرانی بین‌المللی» طبق مقررات بین‌المللی بهداشت (IHR)؛ تصمیمی رسمی از مدیرکل WHO با نظر کمیته‌ی اضطرار.",
           en: "“Public health emergency of international concern” under the International Health Regulations: a formal decision by WHO's Director-General advised by an Emergency Committee." } },
  { id: "r", group: "outbreak", term: { fa: "عدد بازتولید (R)", en: "Reproduction number (R)" },
    def: { fa: "میانگین تعداد افرادی که یک فرد آلوده مبتلا می‌کند. بالای ۱ یعنی رشد، زیر ۱ یعنی کاهش. در این سایت از نرخ رشد و بازه‌ی نسل تقریب زده می‌شود و فقط راهنماست.",
           en: "The average number of people one infected person infects. Above 1 means growth, below 1 means decline. Here it is approximated from the growth rate and generation interval and is only indicative." } },
  { id: "doubling", group: "outbreak", term: { fa: "زمان دو برابر شدن", en: "Doubling time" },
    def: { fa: "زمانی که طول می‌کشد موارد دو برابر شوند؛ از نرخ رشد هفتگی r به‌صورت ln2/r محاسبه می‌شود.",
           en: "How long cases take to double; computed from the weekly growth rate r as ln2 / r." } },
  { id: "baseline", group: "outbreak", term: { fa: "خط پایه و حد بالا", en: "Baseline and upper limit" },
    def: { fa: "سطح مورد انتظار همان هفته‌ی سال بر اساس سال‌های قبل و حدی که بالاتر از آن افزایش از نظر آماری غیرعادی است. فقط از داده‌ی گذشته ساخته می‌شود.",
           en: "The level expected for that week of the year from earlier years, and the limit above which a rise is statistically unusual. Built from past data only." } },
  { id: "quality", group: "data", term: { fa: "گزارش‌شده / برآوردی / مدل‌سازی‌شده", en: "Reported / estimated / modelled" },
    def: { fa: "گزارش‌شده: شمارش سامانه‌ی مراقبت. برآوردی: برآورد WHO/UN از داده‌ی ناقص. مدل‌سازی‌شده: خروجی مدل آماری کامل (مانند GBD). هرگز مدل را با شمارش اشتباه نگیرید.",
           en: "Reported: counted by a surveillance system. Estimated: WHO/UN estimate from partial data. Modelled: output of a full statistical model (such as GBD). Never mistake a model for a count." } },
  { id: "delay", group: "data", term: { fa: "تأخیر گزارش‌دهی", en: "Reporting delay" },
    def: { fa: "داده‌ی هفته‌های اخیر معمولاً بعداً اصلاح می‌شود. افت ناگهانی در آخرین هفته اغلب تأخیر است، نه بهبود.",
           en: "Recent weeks are usually revised later. A sudden drop in the latest week is often delay, not improvement." } },
  { id: "batch", group: "data", term: { fa: "گزارش دسته‌ای", en: "Batch reporting" },
    def: { fa: "برخی کشورها داده را ماهانه یا با تأخیر یکجا گزارش می‌کنند؛ در نمودار هفتگی شبیه جهش دیده می‌شود. سایت آن را تشخیص و میانگین ۴ هفته را استفاده می‌کند.",
           en: "Some countries report monthly or in lumps, which looks like a spike in a weekly chart. The site detects this and uses a 4-week mean." } },
  { id: "icd", group: "data", term: { fa: "ICD-10", en: "ICD-10" },
    def: { fa: "طبقه‌بندی بین‌المللی بیماری‌ها؛ زبان مشترکی که منابع مختلف را به یک بیماری وصل می‌کند.",
           en: "The International Classification of Diseases; the shared language that links different sources to the same disease." } },
];

export interface Lesson {
  slug: "covid-19" | "mpox";
  title: Bi;
  blurb: Bi;
  /** Milestones are from the author's memory: shown with a "verify" notice. */
  milestones: { date: string; text: Bi }[];
  notice: Bi[];
  questions: Bi[];
  /** replay window and API step (1 = weekly) */
  window: { from: string; to: string; step: number };
}

export const LESSONS: Lesson[] = [
  {
    slug: "covid-19",
    window: { from: "2020-01-13", to: "2020-07-27", step: 1 },
    title: { fa: "COVID-19، ۲۰۲۰: یک ویروس نو چطور در نقشه پخش شد", en: "COVID-19, 2020: how a new virus spread across the map" },
    blurb: { fa: "بازپخش هفته‌به‌هفته‌ی داده‌ی JHU؛ هر هفته فقط با داده‌ی همان زمان محاسبه شده است.",
             en: "A week-by-week replay of JHU data; each week is computed only from data available then." },
    milestones: [
      { date: "2020-01-30", text: { fa: "WHO وضعیت PHEIC اعلام کرد", en: "WHO declared a PHEIC" } },
      { date: "2020-03-11", text: { fa: "WHO وضعیت را «پاندمی» توصیف کرد", en: "WHO characterised the situation as a pandemic" } },
    ],
    notice: [
      { fa: "ببینید نخستین پراکندگی در چند منطقه‌ی WHO چه زمانی علامت می‌خورد، و آن را با تاریخ‌های رسمی مقایسه کنید.",
        en: "See when the first spread across several WHO regions is flagged, and compare it with the official dates." },
      { fa: "رنگ قرمز یعنی «بالاتر از حد انتظار» در همان کشور، نه تعداد مطلق موارد.",
        en: "Red means “above expected” for that country, not the absolute number of cases." },
    ],
    questions: [
      { fa: "چرا نقشه چند هفته بعد از اولین موارد هنوز سبک است؟ (راهنمایی: خط پایه و تأخیر گزارش)",
        en: "Why is the map still light weeks after the first cases? (Hint: baseline and reporting delay.)" },
      { fa: "اگر فقط یک کشور قرمز باشد و بقیه نه، آیا می‌توان آن را پاندمی نامید؟",
        en: "If only one country is red, can that be called a pandemic?" },
    ],
  },
  {
    slug: "mpox",
    window: { from: "2022-04-25", to: "2022-12-26", step: 1 },
    title: { fa: "آبله میمونی، ۲۰۲۲: شیوع خارج از مناطق اندمیک", en: "Mpox, 2022: an outbreak outside endemic areas" },
    blurb: { fa: "شیوعی که ناگهان در کشورهایی دیده شد که معمولاً مورد نداشتند.",
             en: "An outbreak that suddenly appeared in countries that normally had no cases." },
    milestones: [
      { date: "2022-05-16", text: { fa: "نخستین اطلاعیه‌ی شیوع WHO (DON)", en: "WHO's first outbreak notice (DON)" } },
      { date: "2022-07-23", text: { fa: "WHO وضعیت PHEIC اعلام کرد", en: "WHO declared a PHEIC" } },
      { date: "2023-05-11", text: { fa: "پایان PHEIC", en: "The PHEIC ended" } },
    ],
    notice: [
      { fa: "«گسترش نوپدید» یعنی موارد نخستین در چند کشور و چند منطقه در عرض چند هفته.",
        en: "“Novel spread” means first-ever cases in several countries and regions within a few weeks." },
      { fa: "برچسب‌ها ممکن است بین دو سطح بالا و پایین بپرند؛ این نشانه‌ی حساسیت روش به گزارش‌دهی نامنظم است.",
        en: "Labels may flip between two levels; that reflects the method's sensitivity to irregular reporting." },
    ],
    questions: [
      { fa: "چرا گزارش ماهانه‌ی برخی کشورها می‌تواند هشدار کاذب بسازد؟",
        en: "Why can monthly reporting from some countries create a false alarm?" },
    ],
  },
];

export const LEARN_TXT = {
  fa: {
    title: "آموزش", lead: "برای دانشجویان و پزشکان: یاد بگیرید آمار بیماری را چطور بخوانید، با داده‌ی واقعی گذشته.",
    lessons: "درس‌ها: بازپخش یک شیوع", glossary: "واژه‌نامه", filter: "جست‌وجو در واژه‌ها",
    groups: { burden: "بار بیماری", outbreak: "شیوع و هشدار", data: "کیفیت داده" },
    milestones: "تاریخ‌های رسمی (از حافظه‌ی نویسنده؛ با منبع WHO تأیید کنید)",
    notice: "به چه چیزی دقت کنیم", questions: "سؤال برای بحث", howto: "چطور نمودار را بخوانیم",
    howtoItems: [
      "همیشه واحد را ببینید: «بر ۱۰۰ هزار نفر» با «تعداد» قابل مقایسه نیست.",
      "برچسب کیفیت را بخوانید: گزارش‌شده، برآوردی و مدل‌سازی‌شده سه چیز متفاوت‌اند.",
      "نوار بازه‌ی عدم قطعیت را نادیده نگیرید؛ تفاوت‌های کوچک‌تر از آن معنا ندارند.",
      "آخرین هفته‌ها را با احتیاط بخوانید؛ تأخیر گزارش‌دهی.",
      "سیگنال آماری، اعلام رسمی نیست.",
    ],
    cite: "برای ارجاع به یک نمودار یا داده از دکمه‌ی «ارجاع» کنار آن استفاده کنید.",
  },
  en: {
    title: "Learn", lead: "For students and clinicians: learn to read disease statistics, using real past data.",
    lessons: "Lessons: replay an outbreak", glossary: "Glossary", filter: "Search terms",
    groups: { burden: "Disease burden", outbreak: "Outbreaks and alerts", data: "Data quality" },
    milestones: "Official dates (from the author's memory; verify against WHO)",
    notice: "What to look for", questions: "Questions for discussion", howto: "How to read the charts",
    howtoItems: [
      "Check the unit: “per 100,000” cannot be compared with a count.",
      "Read the quality label: reported, estimated and modelled are three different things.",
      "Do not ignore the uncertainty band; differences smaller than it mean nothing.",
      "Read the latest weeks with care: reporting delay.",
      "A statistical signal is not an official declaration.",
    ],
    cite: "To cite a chart or dataset use the “Cite” button next to it.",
  },
};
