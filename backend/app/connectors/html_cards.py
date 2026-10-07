"""Mahsulot kartalari ro'yxatini HTML'dan o'qishning umumiy mexanizmi.

Yigirmadan ortiq bank sayti bir xil tuzilishga ega: sahifada takrorlanuvchi
"karta" bloki, uning ichida mahsulot nomi, bir nechta yorliq/qiymat juftligi
va batafsil sahifaga havola. Avval har bir bank uchun shu bir xil algoritm
(tanla → nomni ol → juftliklarni yig' → havolani qo'sh → dublikatni tashla)
qo'lda qayta yozilar edi; farq faqat CSS tanlagichlarda bo'lgani uchun bu
sof takrorlanish edi va bitta xatoni tuzatish yigirma joyni tahrirlashni
talab qilardi.

Bu modul algoritmni bir marta yozadi, har bir bank esa faqat o'z
tanlagichlarini `CardLayout` sifatida e'lon qiladi. Yangi bank qo'shish
mavjud kodga tegmasdan yangi e'lon yozishdan iborat.

Yorliq/qiymat juftligini topish usuli saytdan saytga farq qilgani uchun
(alohida tanlagichlar, `<dt>/<dd>`, qo'shni element, ikkita farzand
element) u alohida `FieldRule` strategiyasi sifatida ajratilgan —
yangi joylashuv turi mavjudlariga tegmasdan qo'shiladi."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag


def base_url_of(url: str) -> str:
    """Manzilning "sxema://host" qismi — nisbiy havolalarni to'liq
    manzilga aylantirish uchun."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_single_product(
    html: str,
    source: str,
    url: str,
    fields: FieldRule,
    min_fields: int = 1,
    clean_name=lambda text: text,
) -> dict | None:
    """Bitta mahsulotning butun sahifasini o'qiydi — ro'yxat sahifasi
    bo'lmagan banklarda (`MultiPageConnector`) har bir sahifa aynan bitta
    mahsulotga bag'ishlangan bo'lganda ishlatiladi: sarlavha ``<h1>``dan,
    ko'rsatkichlar esa `fields` qoidasi bo'yicha butun sahifadan olinadi.

    `clean_name` — ba'zi saytlarda ``<h1>`` mahsulot nomidan tashqari
    reklama shiori bilan davom etadi (masalan "Avtokredit — oson va
    oddiy!") — shunday hollarda xom sarlavha matnidan haqiqiy nomni
    ajratib oluvchi funksiya beriladi.

    Sarlavha topilmasa yoki ko'rsatkichlar soni `min_fields`dan kam bo'lsa
    (masalan 404 sahifasi yoki mahsulot bekor qilingan bo'lsa) `None`
    qaytadi — chaqiruvchi bunday sahifani e'tiborsiz qoldiradi."""
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.select_one("h1")
    if title_el is None:
        return None
    name = clean_name(title_el.get_text(" ", strip=True))
    if not name:
        return None

    record = {"name": name, "source": source, "url": url}
    record.update(fields.extract(soup))
    return record if len(record) - 3 >= min_fields else None


def dedupe_records(records: list[dict]) -> list[dict]:
    """Aynan bir xil yozuvlarni (barcha maydonlari mos keladigan) bir marta
    qoldiradi — tartibni saqlab.

    Ko'p saytlarda bitta mahsulot sahifada bir necha marta chiqadi
    (mobil/desktop ikkilamchi razmetka, filtr yorliqlari, tab'lar) — bu
    haqiqiy takroriy mahsulot emas, bitta yozuvning aks sadosi, shu bois
    umumiy algoritmdan tashqarida qo'lda parser yozadigan connectorlar
    ham (masalan bir xil karta klassi sahifadan sahifaga boshqa-boshqa
    ma'noda ishlatiladigan hollarda) shu bir xil qoidadan foydalanadi."""
    seen: set[tuple] = set()
    deduped = []
    for record in records:
        fingerprint = tuple(sorted(record.items()))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        deduped.append(record)
    return deduped


def _text(node: Tag, separator: str = " ") -> str:
    """Elementning matnini oladi va barcha ichki bo'shliqlarni (jumladan
    manba HTML'idagi tasodifiy qator ko'chirishlarni) bitta bo'shliqqa
    normalizatsiya qiladi."""
    return " ".join(node.get_text(separator).split())


def _has_digit(text: str) -> bool:
    return any(ch.isdigit() for ch in text)


# ─────────────────────────────────────────────────────────────────────
# Yorliq/qiymat juftligini topish strategiyalari
# ─────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class FieldRule:
    """Karta ichidan yorliq/qiymat juftliklarini ajratib oluvchi qoida.

    `strip_colon` — ba'zi saytlar yorliqni "Muddati:" ko'rinishida beradi;
    `swap_on_digits` — ba'zi shablonlarda yorliq va qiymat tartibi izchil
    emas, shu bois raqam saqlagan tomon qiymat deb hisoblanadi;
    `max_length` — reklama matni uchun qayta ishlatilgan bir xil
    razmetkani haqiqiy ko'rsatkichdan ajratish uchun uzunlik chegarasi."""

    strip_colon: bool = False
    swap_on_digits: bool = False
    max_length: int | None = None
    value_separator: str = " "

    def extract(self, card: Tag) -> Iterator[tuple[str, str]]:
        for label, value in self._pairs(card):
            pair = self._normalize(label, value)
            if pair:
                yield pair

    def _pairs(self, card: Tag) -> Iterator[tuple[str, str]]:
        raise NotImplementedError

    def _normalize(self, label: str, value: str) -> tuple[str, str] | None:
        if self.swap_on_digits and _has_digit(label) and not _has_digit(value):
            label, value = value, label
        if self.strip_colon:
            label = label.rstrip(":").strip()
        if not label or not value:
            return None
        if self.max_length is not None and (len(label) > self.max_length or len(value) > self.max_length):
            return None
        return label, value


@dataclass(frozen=True)
class SelectedFields(FieldRule):
    """Eng keng tarqalgan joylashuv: har bir juftlik o'z o'ram elementida,
    yorliq va qiymat esa uning ichidagi alohida tanlagichlar bilan
    belgilangan (`<dt>/<dd>` ham shu qoidaga tushadi)."""

    container: str = ""
    label: str = ""
    value: str = ""

    def _pairs(self, card: Tag) -> Iterator[tuple[str, str]]:
        for block in card.select(self.container):
            label_el = block.select_one(self.label)
            value_el = block.select_one(self.value)
            if label_el and value_el:
                yield _text(label_el), _text(value_el, self.value_separator)


@dataclass(frozen=True)
class SiblingFields(FieldRule):
    """Yorliq va qiymat bitta o'ramga o'ralmagan — qiymat yorliqdan keyingi
    qo'shni element sifatida keladi."""

    label: str = ""
    value_tag: str = "div"

    def _pairs(self, card: Tag) -> Iterator[tuple[str, str]]:
        for label_el in card.select(self.label):
            value_el = label_el.find_next_sibling(self.value_tag)
            if value_el:
                yield _text(label_el), _text(value_el, self.value_separator)


@dataclass(frozen=True)
class ChildPairFields(FieldRule):
    """Juftlik o'ramning aynan ikkita farzand elementidan iborat.
    `value_first` — ko'p saytlarda avval yirik qiymat, keyin kichik
    yorliq ko'rsatiladi (vizual ustuvorlik tartibi)."""

    container: str = ""
    value_first: bool = True
    child_tags: tuple[str, ...] = ()

    def _pairs(self, card: Tag) -> Iterator[tuple[str, str]]:
        for block in card.select(self.container):
            children = self._children(block)
            if len(children) != 2:
                continue
            first, second = (_text(c, self.value_separator) for c in children)
            yield (second, first) if self.value_first else (first, second)

    def _children(self, block: Tag) -> list[Tag]:
        if len(set(self.child_tags)) == 1:
            # Ikkalasi ham bir xil teg (masalan ikkita <p>) — nomi bo'yicha
            # emas, pozitsiyasi bo'yicha ajratiladi.
            return block.find_all(self.child_tags[0], recursive=False)[: len(self.child_tags)]
        if self.child_tags:
            found = [block.find(tag, recursive=False) for tag in self.child_tags]
            return [node for node in found if node is not None]
        return block.find_all(True, recursive=False)


@dataclass(frozen=True)
class FirstMatchFields(FieldRule):
    """Bir nechta strategiyani ustuvorlik tartibida sinaydi va birinchi
    natija bergan qoidaning juftliklarini qaytaradi.

    Ba'zi saytlarda bitta CSS klass (masalan bitta umumiy "karta" bloki)
    sahifadan sahifaga (omonat/kredit/karta) butunlay boshqa ichki
    tuzilishda ishlatiladi — har bir sahifa turi o'zining qoidasi bilan
    mos keladi, qolganlari hech narsa topmay bo'sh qaytadi."""

    rules: tuple[FieldRule, ...] = ()

    def extract(self, card: Tag) -> Iterator[tuple[str, str]]:
        for rule in self.rules:
            pairs = list(rule.extract(card))
            if pairs:
                return iter(pairs)
        return iter(())


# ─────────────────────────────────────────────────────────────────────
# Karta ro'yxati e'loni va uni o'qiydigan yagona algoritm
# ─────────────────────────────────────────────────────────────────────
Selector = str | tuple[str, ...]


def _select_first(node: Tag, selector: Selector) -> Tag | None:
    """Bir nechta tanlagich berilsa, ular hujjatdagi tartibiga emas,
    berilgan ustuvorlik tartibiga qarab sinab ko'riladi — bitta saytning
    turli shablonlari bir xil kartada ikki xil belgi ishlatganda qaysi
    biri ustun turishini e'lonning o'zi belgilaydi."""
    if isinstance(selector, str):
        return node.select_one(selector)
    for candidate in selector:
        found = node.select_one(candidate)
        if found:
            return found
    return None


@dataclass(frozen=True)
class CardLayout:
    """Bitta saytdagi mahsulot kartalari ro'yxatining tavsifi.

    `link` berilmasa, batafsil havola sarlavha elementining o'zidan (yoki
    uning ichidagi `<a>`dan) olinadi — ko'p saytlarda sarlavhaning o'zi
    havola bo'ladi. `link_text` berilsa, kartadagi havolalar orasidan
    aynan shu matnli bittasi tanlanadi. `title` va `link` uchun tuple
    berilsa, tanlagichlar ustuvorlik tartibida sinaladi. `link_attr` —
    havola manzili "href"dan boshqa atributda kelganda (masalan Angular
    ``routerlink``)."""

    source: str
    card: str
    title: Selector
    fields: FieldRule
    link: Selector | None = None
    link_text: str | None = None
    link_from_card: bool = False
    link_attr: str = "href"
    extra: dict[str, str] = field(default_factory=dict)


def _find_href(card: Tag, title_el: Tag, layout: CardLayout) -> str | None:
    if layout.link_from_card:
        return card.get("href")
    if layout.link_text is not None:
        for link in card.select("a[href]"):
            if link.get_text(strip=True) == layout.link_text:
                return link.get("href")
        return None
    if layout.link:
        link = _select_first(card, layout.link)
        return link.get(layout.link_attr) if link is not None else None
    if title_el.name == "a":
        return title_el.get("href")
    nested = title_el.find("a", href=True)
    return nested.get("href") if nested is not None else None


def parse_card_list(html: str, layout: CardLayout, base_url: str) -> list[dict]:
    """`layout` tavsifi bo'yicha sahifadagi barcha mahsulot kartalarini
    normalizatsiya qilingan dict'lar ro'yxatiga aylantiradi.

    Bir xil mahsulot sahifada bir necha marta (mobil/desktop razmetkasi,
    filtr yorliqlari) chiqishi mumkin — aynan bir xil yozuvlar bir marta
    qoldiriladi."""
    soup = BeautifulSoup(html, "html.parser")
    records: list[dict] = []

    for card in soup.select(layout.card):
        title_el = _select_first(card, layout.title)
        if title_el is None:
            continue
        name = title_el.get_text(strip=True)
        if not name:
            continue

        record = {"name": name, "source": layout.source, **layout.extra}
        record.update(layout.fields.extract(card))

        href = _find_href(card, title_el, layout)
        if href:
            record["url"] = urljoin(base_url, href.strip())

        records.append(record)

    return dedupe_records(records)
