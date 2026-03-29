# patch_harbor_filter.py — Семантический фильтр для Гавани Смыслов
# Проблема: в выдаче лезет мусор (окна ПВХ при поиске "история про смелость")
# Решение: порог min_score=0.38 + возможность исключать категории
#
# Запуск: python patch_harbor_filter.py
# Студия «Шесть Пальцев» · Грондхейм · 2026

from pathlib import Path
import shutil

TARGET = Path("studio/harbor_of_meanings.py")

if not TARGET.exists():
    print("❌ studio/harbor_of_meanings.py не найден!")
    print("   Запусти из корня проекта (там где main.py)")
    exit(1)

content = TARGET.read_text(encoding="utf-8")
backup = TARGET.with_suffix(".py.bak")
shutil.copy(TARGET, backup)
print(f"💾 Бэкап: {backup}")

fixes = 0

# ═══════════════════════════════════════════════════
# FIX 1: search_harbor — добавить min_score и exclude_categories
# ═══════════════════════════════════════════════════

old_signature = '''def search_harbor(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    category: str = None,
    dept: str = None,
) -> list[dict]:
    """
    Поиск по Гавани Смыслов.

    Args:
        query: что ищем (текст запроса)
        top_k: сколько результатов
        category: фильтр по категории (set_knowledge, project_results, city_lore, agent_knowledge)
        dept: фильтр по цеху

    Returns:
        Список результатов: [{"text": "...", "source": "...", "score": 0.85, ...}]
    """'''

new_signature = '''def search_harbor(
    query: str,
    top_k: int = DEFAULT_TOP_K,
    category: str = None,
    dept: str = None,
    min_score: float = 0.38,
    exclude_categories: list = None,
) -> list[dict]:
    """
    Поиск по Гавани Смыслов.

    Args:
        query: что ищем (текст запроса)
        top_k: сколько результатов
        category: фильтр по категории (set_knowledge, project_results, city_lore, agent_knowledge)
        dept: фильтр по цеху
        min_score: минимальный порог релевантности (0.0–1.0). По умолчанию 0.38.
                   Всё ниже — мусор, не попадает в выдачу.
                   Примечание: paraphrase-multilingual-MiniLM-L12-v2 редко даёт > 0.55
                   на смешанном контенте, поэтому 0.6 отрежет всё.
        exclude_categories: список категорий которые исключить из выдачи.
                   Например: ["project_results"] уберёт архивы клиентских проектов.

    Returns:
        Список результатов: [{"text": "...", "source": "...", "score": 0.85, ...}]
    """'''

if old_signature in content:
    content = content.replace(old_signature, new_signature)
    fixes += 1
    print("✅ FIX 1: сигнатура search_harbor — добавлены min_score и exclude_categories")
else:
    print("⚠️  FIX 1: сигнатура не найдена (возможно уже применён)")

# ═══════════════════════════════════════════════════
# FIX 2: блок форматирования результатов — вставить фильтрацию
# ═══════════════════════════════════════════════════

old_format = '''    # Форматируем результаты
    output = []
    if results and results.get("documents") and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            output.append({
                "text": doc,
                "source": meta.get("source", ""),
                "category": meta.get("category", ""),
                "score": round(1.0 - dist, 3),  # cosine distance → similarity
                "metadata": meta,
            })

    return output'''

new_format = '''    # Форматируем результаты
    output = []
    if results and results.get("documents") and results["documents"][0]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(docs)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(docs)

        for doc, meta, dist in zip(docs, metas, distances):
            score = round(1.0 - dist, 3)  # cosine distance → similarity

            # ── Фильтр 1: порог релевантности ──
            if score < min_score:
                continue

            # ── Фильтр 2: исключить нежелательные категории ──
            cat = meta.get("category", "")
            if exclude_categories and cat in exclude_categories:
                continue

            output.append({
                "text": doc,
                "source": meta.get("source", ""),
                "category": cat,
                "score": score,
                "metadata": meta,
            })

    if not output:
        print(f"[ГАВАНЬ] 🔇 Релевантных данных не обнаружено (порог {min_score:.0%})")

    return output'''

if old_format in content:
    content = content.replace(old_format, new_format)
    fixes += 1
    print("✅ FIX 2: блок фильтрации результатов добавлен")
else:
    print("⚠️  FIX 2: блок форматирования не найден (возможно уже применён)")

# ═══════════════════════════════════════════════════
# FIX 3: CLI --search — добавить сообщение если ничего не нашлось
# ═══════════════════════════════════════════════════

old_cli = '''    results = search_harbor(query)
        for r in results:
            print(f"\\n[{r['score']:.0%}] {r['category']}")
            print(f"  {r['text'][:200]}")
            print(f"  📄 {r['source']}")'''

new_cli = '''    results = search_harbor(query)
        if not results:
            print("🔇 Релевантных данных не обнаружено")
        for r in results:
            print(f"\\n[{r['score']:.0%}] {r['category']}")
            print(f"  {r['text'][:200]}")
            print(f"  📄 {r['source']}")'''

if old_cli in content:
    content = content.replace(old_cli, new_cli)
    fixes += 1
    print("✅ FIX 3: CLI --search — добавлено сообщение 'Релевантных данных не обнаружено'")
else:
    # Пробуем без отступов (на случай разного форматирования)
    old_cli2 = '''    results = search_harbor(query)
    for r in results:
        print(f"\\n[{r['score']:.0%}] {r['category']}")
        print(f"  {r['text'][:200]}")
        print(f"  📄 {r['source']}")'''

    new_cli2 = '''    results = search_harbor(query)
    if not results:
        print("🔇 Релевантных данных не обнаружено")
    for r in results:
        print(f"\\n[{r['score']:.0%}] {r['category']}")
        print(f"  {r['text'][:200]}")
        print(f"  📄 {r['source']}")'''

    if old_cli2 in content:
        content = content.replace(old_cli2, new_cli2)
        fixes += 1
        print("✅ FIX 3: CLI --search — добавлено сообщение 'Релевантных данных не обнаружено'")
    else:
        print("⚠️  FIX 3: CLI блок не найден (добавь вручную после results = search_harbor(query))")

# ═══════════════════════════════════════════════════
# Сохраняем
# ═══════════════════════════════════════════════════

if fixes > 0:
    TARGET.write_text(content, encoding="utf-8")
    print(f"\n💾 Сохранено: {TARGET} ({fixes} фиксов)")
    print(f"   Бэкап: {backup}")
else:
    print("\n⚠️  Ничего не изменено — все фиксы уже применены?")
    backup.unlink(missing_ok=True)

print(f"""
═══════════════════════════════════════
  ИТОГ: Гавань получила смысловой фильтр
═══════════════════════════════════════

  ✅ min_score=0.38 — мусор ниже 38% не попадает в выдачу
  ✅ exclude_categories — можно исключить project_results
     если нужен только лор/знания

  Почему 0.38, а не 0.6 (как предлагала Лока):
    paraphrase-multilingual-MiniLM-L12-v2 физически
    не даёт > 0.55 на смешанном контенте.
    Порог 0.6 = пустая выдача всегда.
    Порог 0.38 = отсекает явный мусор, оставляет суть.

  Как использовать:
    # Только лор и знания (без клиентских проектов):
    search_harbor("история про смелость", exclude_categories=["project_results"])

    # Повысить планку (строже):
    search_harbor("история про смелость", min_score=0.45)

    # CLI (стандартный, с фильтром по умолчанию):
    python -m studio.harbor_of_meanings --search "история про смелость"
""")
