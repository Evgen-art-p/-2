"""
generate_report_pdf.py — Генерирует PDF-отчёт из logic_map.json
Встраивается в кнопку 🧠 LOGIC сборочного цеха.

Использование:
    from studio.generate_report_pdf import generate_project_pdf
    generate_project_pdf(logic_map, output_path, project_title="...")
"""

import json
from pathlib import Path
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# ────────────────────────────────────────────────────────────
# ЦВЕТА
# ────────────────────────────────────────────────────────────

C_BG       = HexColor("#0d1117")
C_CARD     = HexColor("#161b22")
C_ACCENT   = HexColor("#ff9500")
C_GREEN    = HexColor("#00cc66")
C_BLUE     = HexColor("#0099dd")
C_PINK     = HexColor("#dd4488")
C_MUTED    = HexColor("#666677")
C_TEXT     = HexColor("#222222")
C_LIGHT    = HexColor("#555566")
C_WHITE    = HexColor("#ffffff")
C_WARN     = HexColor("#cc6600")
C_HEADER_BG = HexColor("#1a1f2e")
C_ROW_ALT  = HexColor("#f4f6f8")
C_ROW_WHT  = HexColor("#ffffff")


# ────────────────────────────────────────────────────────────
# СТИЛИ
# ────────────────────────────────────────────────────────────

def _build_styles():
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "Title2",
        parent=styles["Title"],
        fontSize=22,
        leading=28,
        textColor=C_ACCENT,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        fontSize=10,
        textColor=C_MUTED,
        spaceAfter=16,
    ))
    styles.add(ParagraphStyle(
        "SectionHead",
        parent=styles["Heading2"],
        fontSize=14,
        textColor=C_ACCENT,
        spaceBefore=20,
        spaceAfter=8,
        borderPadding=(0, 0, 4, 0),
    ))
    styles.add(ParagraphStyle(
        "SceneName",
        parent=styles["Heading3"],
        fontSize=11,
        textColor=C_TEXT,
        spaceBefore=10,
        spaceAfter=2,
    ))
    styles.add(ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=C_TEXT,
    ))
    styles.add(ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=C_LIGHT,
    ))
    styles.add(ParagraphStyle(
        "Dialogue",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=C_TEXT,
        leftIndent=12,
        borderPadding=(0, 0, 0, 8),
    ))
    styles.add(ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=C_TEXT,
    ))
    styles.add(ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontSize=8,
        leading=11,
        textColor=C_WHITE,
        fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        "CheckItem",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=C_TEXT,
        leftIndent=16,
        bulletIndent=0,
    ))
    return styles


# ────────────────────────────────────────────────────────────
# ГЕНЕРАЦИЯ
# ────────────────────────────────────────────────────────────

def generate_project_pdf(logic_map: dict, output_path: str,
                         project_title: str = None,
                         warnings: list = None) -> str:
    """
    Генерирует PDF-отчёт проекта.

    Args:
        logic_map: dict из extract_logic()
        output_path: путь для PDF
        project_title: название проекта (опционально)
        warnings: список предупреждений QA (опционально)

    Returns:
        str — путь к готовому PDF
    """
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=18*mm,
        bottomMargin=18*mm,
    )

    S = _build_styles()
    story = []
    W = doc.width  # доступная ширина

    pid = logic_map.get("project_id", "unknown")
    title = project_title or pid
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    # ── ЗАГОЛОВОК ──
    story.append(Paragraph(f"<b>{title}</b>", S["Title2"]))
    story.append(Paragraph(
        f"Проект: {pid}  |  Дата: {now}  |  "
        f"Источник: {logic_map.get('source_file', '?')}",
        S["Subtitle"]
    ))

    # Статистика
    scenes = logic_map.get("scenes", [])
    branches = logic_map.get("branches", [])
    interactions = logic_map.get("interactions", [])
    achievements = logic_map.get("achievements", [])
    sound_map = logic_map.get("sound_map", [])

    stats_data = [[
        Paragraph("<b>Сцен</b>", S["TableHeader"]),
        Paragraph("<b>Веток</b>", S["TableHeader"]),
        Paragraph("<b>Интерактив</b>", S["TableHeader"]),
        Paragraph("<b>Достижений</b>", S["TableHeader"]),
        Paragraph("<b>Звук-карт</b>", S["TableHeader"]),
    ], [
        Paragraph(f"<b>{len(scenes)}</b>", S["TableCell"]),
        Paragraph(f"<b>{len(branches)}</b>", S["TableCell"]),
        Paragraph(f"<b>{len(interactions)}</b>", S["TableCell"]),
        Paragraph(f"<b>{len([a for a in achievements if a.get('condition') != 'meta'])}</b>", S["TableCell"]),
        Paragraph(f"<b>{len(sound_map)}</b>", S["TableCell"]),
    ]]
    stats_t = Table(stats_data, colWidths=[W/5]*5)
    stats_t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
        ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
        ("BACKGROUND", (0, 1), (-1, 1), C_ROW_WHT),
        ("GRID", (0, 0), (-1, -1), 0.5, C_MUTED),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    story.append(stats_t)
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", color=C_MUTED, thickness=0.5))

    # ══════════════════════════════════════════════════════════
    # 1. СЦЕНЫ
    # ══════════════════════════════════════════════════════════
    story.append(Paragraph("1. СЦЕНЫ", S["SectionHead"]))

    for s in scenes:
        order = s.get("order", "?")
        name = s.get("scene_name", "")
        emotion = s.get("emotion", "")
        location = s.get("location", "")
        text = s.get("text", "")

        story.append(Paragraph(
            f'<b>Сцена {order}.</b>  {_esc(name)}',
            S["SceneName"]
        ))

        if emotion:
            story.append(Paragraph(
                f'<font color="#dd4488"><i>{_esc(emotion)}</i></font>',
                S["Small"]
            ))
        if location:
            story.append(Paragraph(
                f'<font color="#0099dd">{_esc(location)}</font>',
                S["Small"]
            ))
        if text:
            # Split dialogues
            for line in text.split(" | "):
                line = line.strip()
                if not line:
                    continue
                story.append(Paragraph(f'"{_esc(line)}"', S["Dialogue"]))

        story.append(Spacer(1, 6))

    # ══════════════════════════════════════════════════════════
    # 2. ЗВУКОВАЯ КАРТА
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("2. ЗВУКОВАЯ КАРТА", S["SectionHead"]))

    if sound_map:
        s_header = [
            Paragraph("<b>Сцена</b>", S["TableHeader"]),
            Paragraph("<b>Эмоция</b>", S["TableHeader"]),
            Paragraph("<b>Музыка</b>", S["TableHeader"]),
            Paragraph("<b>Амбиент</b>", S["TableHeader"]),
            Paragraph("<b>SFX</b>", S["TableHeader"]),
        ]
        s_rows = [s_header]
        for sm in sound_map:
            s_rows.append([
                Paragraph(f'<b>{sm.get("scene_id","")}</b>', S["TableCell"]),
                Paragraph(_esc(sm.get("emotion", "")), S["TableCell"]),
                Paragraph(_esc(sm.get("music", "")), S["TableCell"]),
                Paragraph(_esc(sm.get("ambient", "")), S["TableCell"]),
                Paragraph(_esc(sm.get("sfx", "-")), S["TableCell"]),
            ])

        col_w = [W*0.12, W*0.18, W*0.28, W*0.22, W*0.20]
        s_table = Table(s_rows, colWidths=col_w, repeatRows=1)
        s_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_ROW_WHT, C_ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.4, C_MUTED),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(s_table)

    # ══════════════════════════════════════════════════════════
    # 3. ДОСТИЖЕНИЯ
    # ══════════════════════════════════════════════════════════
    story.append(Spacer(1, 12))
    story.append(Paragraph("3. ДОСТИЖЕНИЯ", S["SectionHead"]))

    real_achs = [a for a in achievements if a.get("condition") != "meta"]
    if real_achs:
        a_header = [
            Paragraph("<b>Иконка</b>", S["TableHeader"]),
            Paragraph("<b>Название</b>", S["TableHeader"]),
            Paragraph("<b>Условие</b>", S["TableHeader"]),
            Paragraph("<b>Награда</b>", S["TableHeader"]),
        ]
        a_rows = [a_header]
        for a in real_achs:
            a_rows.append([
                Paragraph(a.get("icon", "?"), S["TableCell"]),
                Paragraph(f'<b>{_esc(a.get("name", ""))}</b>', S["TableCell"]),
                Paragraph(_esc(str(a.get("condition", ""))), S["TableCell"]),
                Paragraph(_esc(str(a.get("reward", ""))), S["TableCell"]),
            ])

        a_table = Table(a_rows, colWidths=[W*0.08, W*0.22, W*0.45, W*0.25], repeatRows=1)
        a_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), C_HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), C_WHITE),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [C_ROW_WHT, C_ROW_ALT]),
            ("GRID", (0, 0), (-1, -1), 0.4, C_MUTED),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(a_table)

    # ══════════════════════════════════════════════════════════
    # 4. ИНТЕРАКТИВ
    # ══════════════════════════════════════════════════════════
    story.append(Spacer(1, 12))
    story.append(Paragraph("4. ИНТЕРАКТИВ", S["SectionHead"]))

    for ix in interactions:
        iid = ix.get("interaction_id", "?")
        sid = ix.get("scene_id", "?")
        elements = ix.get("elements", [])
        story.append(Paragraph(
            f'<b>{_esc(iid)}</b> <font color="#666677">(сцена: {_esc(sid)})</font>',
            S["Body"]
        ))
        if elements:
            for el in elements[:5]:
                if isinstance(el, dict):
                    el_text = f'{el.get("element_id", "?")}: {el.get("prompt", "")[:60]}'
                else:
                    el_text = str(el)[:80]
                story.append(Paragraph(f'  - {_esc(el_text)}', S["Small"]))
        story.append(Spacer(1, 6))

    # ══════════════════════════════════════════════════════════
    # 5. ПРЕДУПРЕЖДЕНИЯ QA
    # ══════════════════════════════════════════════════════════
    if warnings:
        story.append(Spacer(1, 12))
        story.append(Paragraph("5. ПРЕДУПРЕЖДЕНИЯ QA", S["SectionHead"]))
        for w in warnings:
            desc = w if isinstance(w, str) else w.get("description", str(w))
            story.append(Paragraph(f'<font color="#cc6600">⚠️</font> {_esc(desc)}', S["Body"]))
            story.append(Spacer(1, 4))

    # ══════════════════════════════════════════════════════════
    # 6. ЧЕКЛИСТ СБОРКИ
    # ══════════════════════════════════════════════════════════
    story.append(PageBreak())
    story.append(Paragraph("ЧЕКЛИСТ СБОРКИ", S["SectionHead"]))

    checklist_sections = [
        ("1. Генерация изображений (Нова)", [
            f"Сцена {s.get('order')}: {s.get('scene_name', '')}" for s in scenes
        ] + ["Бейджи достижений (x5)", "UI-кнопки выбора пути (x2)"]),

        ("2. Звук и голос (Рэй)", [
            "Основной трек: calm instrumental, 70 BPM",
            "Вариации треков (сцены 1, 2, 7)",
            "SFX: ветер, рулетка, герметик, свеча",
            "TTS: Мастер Петр (мужской, бас)",
            "TTS: Клиент (женский, настороженность -> благодарность)",
        ]),

        ("3. Вёрстка и логика", [
            "Вёрстка всех сцен",
            "Выбор пути: полный / экспресс (сцена 2)",
            "Навигация: Назад / Меню",
            "Интеграция звуковой карты",
            "Геймификация: теплики, достижения, прогресс",
            "CTA: кнопка «Заявка на замер»",
            "Шеринг: Telegram + WhatsApp",
        ]),

        ("4. QA и запуск", [
            "⚠️ Проверить TTS голоса",
            "⚠️ Проверить сгенерированные SFX",
            "Аналитика: event_buffer, admin-страница",
            "A/B конфиг для CTA",
            "GDPR — нет персональных данных",
            "Тест на мобильном",
            "Публикация",
        ]),
    ]

    for section_title, items in checklist_sections:
        story.append(Spacer(1, 8))
        story.append(Paragraph(f'<b>{section_title}</b>', S["Body"]))
        story.append(Spacer(1, 4))
        for item in items:
            # Unicode checkbox
            story.append(Paragraph(
                f'<font color="#999999">☐</font>  {_esc(item)}',
                S["CheckItem"]
            ))

    # ── Footer note ──
    story.append(Spacer(1, 24))
    story.append(HRFlowable(width="100%", color=C_MUTED, thickness=0.5))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        f'Сгенерировано студией Six Fingers  |  {now}  |  {pid}',
        S["Small"]
    ))

    # BUILD
    doc.build(story)
    print(f"📄 PDF готов: {out}")
    return str(out)


def _esc(text: str) -> str:
    """Экранирование XML-спецсимволов для ReportLab Paragraph."""
    if not text:
        return ""
    return (str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ────────────────────────────────────────────────────────────
# CLI
# ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("python generate_report_pdf.py <logic_map.json> [output.pdf]")
        sys.exit(1)

    lm = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    out = sys.argv[2] if len(sys.argv) > 2 else f"{lm.get('project_id', 'project')}_report.pdf"
    generate_project_pdf(lm, out)
