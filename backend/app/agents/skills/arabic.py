"""Arabic language support for extraction (PLAN §12, Phase 3).

Deterministic helpers only — no LLM dependency:
- language detection (Arabic vs Latin character ratios),
- Arabic text normalization (diacritics, alef/ya/ta-marbuta unification),
- canonical skill mapping from Arabic aliases to the English taxonomy.
"""

from __future__ import annotations

import re
import unicodedata

ARABIC_RANGE = re.compile(r"[\u0600-\u06FF]")
LATIN_RANGE = re.compile(r"[A-Za-z]")

# Diacritics (harakat), tatweel (kashida), and Quranic annotation marks.
_DIACRITICS = re.compile(r"[\u064B-\u065F\u0670\u0640\u06D6-\u06ED]")

_ALEF_UNIFY = {"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا"}
_YA_UNIFY = {"ى": "ي", "ئ": "ي"}
_WAW_UNIFY = {"ؤ": "و"}
_TA_MARBUTA = {"ة": "ه"}


def detect_language(text: str) -> str:
    """Return 'ar', 'en', or 'mixed' from character ratios."""
    arabic = len(ARABIC_RANGE.findall(text or ""))
    latin = len(LATIN_RANGE.findall(text or ""))
    if arabic == 0 and latin == 0:
        return "en"
    if arabic == 0:
        return "en"
    if latin == 0:
        return "ar"
    ratio = arabic / (arabic + latin)
    if ratio >= 0.6:
        return "ar"
    if ratio <= 0.4:
        return "en"
    return "mixed"


def normalize_arabic(text: str) -> str:
    """Normalize Arabic orthography for matching (no case folding needed)."""
    text = unicodedata.normalize("NFC", text or "")
    text = _DIACRITICS.sub("", text)
    for mapping in (_ALEF_UNIFY, _YA_UNIFY, _WAW_UNIFY, _TA_MARBUTA):
        for original, replacement in mapping.items():
            text = text.replace(original, replacement)
    return re.sub(r"\s+", " ", text).strip()


def normalize_text_multilingual(text: str) -> str:
    """Lowercase Latin, normalize Arabic, collapse whitespace."""
    return re.sub(r"\s+", " ", normalize_arabic(text or "").lower()).strip()


# Arabic alias -> canonical English skill name (taxonomy in data/seed/skills.json).
ARABIC_ALIASES: dict[str, str] = {
    "بايثون": "Python",
    "جافا": "Java",
    "جافاسكريبت": "JavaScript",
    "قواعد البيانات": "SQL",
    "اكسل": "Excel",
    "دوكرب": "Docker",
    "كبارنتس": "Kubernetes",
    "تعلم الالة": "Machine Learning",
    "الذكاء الاصطناعي": "Generative AI",
    "الامن السيبراني": "Cybersecurity",
    "شبكات": "Network Security",
    "محاسبة": "Accounting",
    "المعايير الدولية": "IFRS",
    "ضريبة": "VAT",
    "تقارير مالية": "Financial Reporting",
    "تحليل مالي": "Financial Analysis",
    "موازنة": "Budgeting",
    "تنبؤ": "Forecasting",
    "تسويق": "Marketing Analytics",
    "التسويق الرقمي": "Digital Marketing",
    "تحسين محركات البحث": "SEO",
    "الموارد البشرية": "Human Resources",
    "توظيف": "Recruitment",
    "ادارة الاداء": "Performance Management",
    "قانون العمل": "Qatar Labor Law",
    "تمريض": "Nursing",
    "رعاية المرضى": "Patient Care",
    "الهندسة المدنية": "Civil Engineering",
    "الهندسة الميكانيكية": "Mechanical Engineering",
    "الهندسة الكهربائية": "Electrical Engineering",
    "ادارة المشاريع": "Project Management",
    "ادارة الانشاءات": "Construction Management",
    "السلامة": "Safety Management",
    "التواصل": "Communication",
    "القيادة": "Leadership",
    "العمل الجماعي": "Teamwork",
    "حل المشكلات": "Problem Solving",
    "الانجليزية": "English",
    "العربية": "Arabic",
    "خدمة العملاء": "Customer Service",
    "الخدمات اللوجستية": "Logistics",
    "سلسلة الامداد": "Supply Chain",
    "المشتريات": "Procurement",
    "تخطيط": "Project Planning",
    "ادارة العقود": "Contract Management",
    "قانون": "Contract Law",
    "التدريس": "Teaching",
    "اوتوكاد": "AutoCAD",
    "اتوكاد": "AutoCAD",
    "واجهات برمجه التطبيقات": "REST APIs",
    "التخليص الجمركي": "Customs Clearance",
    "اداره المخزون": "Inventory Management",
    "اداره الوقت": "Time Management",
    "مكافحه العدوي": "Infection Control",
}

REQUIRED_CUES_AR = ("مطلوب", "ضروري", "يجب", "اساسي", "الزامي")
PREFERRED_CUES_AR = ("يفضل", "ميزه", "مرغوب", "ليس ضروريا")


def find_arabic_skill_mentions(text: str) -> list[tuple[str, int, int, str]]:
    """Return (canonical_name, start, end, matched_alias) from normalized text."""
    normalized = normalize_text_multilingual(text)
    mentions: list[tuple[str, int, int, str]] = []
    occupied: list[tuple[int, int]] = []
    # Longest aliases first so specific phrases win over substrings.
    for alias, canonical in sorted(
        ARABIC_ALIASES.items(), key=lambda item: len(normalize_arabic(item[0])), reverse=True
    ):
        normalized_alias = normalize_arabic(alias)
        for match in re.finditer(re.escape(normalized_alias), normalized):
            start, end = match.span()
            if any(start < other_end and end > other_start for other_start, other_end in occupied):
                continue
            occupied.append((start, end))
            mentions.append((canonical, start, end, normalized_alias))
    return sorted(mentions, key=lambda item: item[1])
