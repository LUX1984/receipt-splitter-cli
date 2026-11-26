from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import html


@dataclass(frozen=True)
class BillItem:
    idx: int
    name: str
    qty: float
    total_price: float


def compute_settlement(
    *,
    items: list[BillItem],
    claims: dict[int, dict[int, str]],  # item_idx -> {user_id: display_name}
    tip_percent: int,
    discount: float = 0.0,
    service_fee: float = 0.0,
) -> tuple[dict[str, float], float, list[BillItem]]:
    """Compute per-person totals including proportional service fee/discount and tips.
    Returns (person_totals_by_name, unclaimed_sum, unclaimed_items).
    """
    totals_by_uid: dict[int, float] = defaultdict(float)
    names: dict[int, str] = {}
    unclaimed: list[BillItem] = []
    claimed_subtotal = 0.0

    for it in items:
        claimers = claims.get(it.idx, {})
        if not claimers:
            unclaimed.append(it)
            continue
        share = it.total_price / len(claimers)
        claimed_subtotal += it.total_price
        for uid, uname in claimers.items():
            names[uid] = uname
            totals_by_uid[uid] += share

    all_items_sum = sum(i.total_price for i in items)
    extra_ratio = 1.0
    if all_items_sum > 0:
        adjusted = max(0.0, all_items_sum - discount + service_fee)
        extra_ratio = adjusted / all_items_sum

    tip_mult = 1.0 + max(0, tip_percent) / 100.0
    person_totals: dict[str, float] = {}
    for uid, base_amt in totals_by_uid.items():
        label = names.get(uid, f"User {uid}")
        if label in person_totals:
            label = f"{label} ({str(uid)[-4:]})"
        person_totals[label] = round(base_amt * extra_ratio * tip_mult, 2)

    unclaimed_sum = round(sum(i.total_price for i in unclaimed) * extra_ratio * tip_mult, 2)
    return person_totals, unclaimed_sum, unclaimed


def format_bill_text(
    *,
    venue: str,
    currency: str,
    items: list[BillItem],
    claims: dict[int, dict[int, str]],
    tip_percent: int,
    discount: float,
    service_fee: float,
    show_settlement: bool,
    footer_free: bool,
    bot_username: str,
) -> str:
    cur = html.escape(currency or "₽")
    title = html.escape(venue or "Чек")
    lines = [f"🧾 <b>{title}</b>"]
    if service_fee > 0:
        lines.append(f"Сервис: +{service_fee:.2f} {cur}")
    if discount > 0:
        lines.append(f"Скидка: -{discount:.2f} {cur}")
    if tip_percent > 0:
        lines.append(f"Чаевые: +{tip_percent}%")
    lines.append("")

    for it in items:
        claimers = list(claims.get(it.idx, {}).values())
        who = f" → <i>{html.escape(', '.join(claimers))}</i>" if claimers else " → <i>не выбран</i>"
        qty_str = f" ×{it.qty:g}" if it.qty and abs(it.qty - 1.0) > 0.01 else ""
        lines.append(f"{it.idx + 1}. {html.escape(it.name)}{qty_str} — <b>{it.total_price:.2f} {cur}</b>{who}")

    person_totals, unclaimed_sum, _ = compute_settlement(
        items=items,
        claims=claims,
        tip_percent=tip_percent,
        discount=discount,
        service_fee=service_fee,
    )
    grand = round(sum(person_totals.values()) + unclaimed_sum, 2)
    lines.append(f"\n💰 Итого по чеку: <b>{grand:.2f} {cur}</b>")

    if show_settlement:
        lines.append("\n<b>🧮 Кто сколько платит:</b>")
        if person_totals:
            for person, amt in sorted(person_totals.items(), key=lambda x: -x[1]):
                lines.append(f"• {html.escape(person)}: <b>{amt:.2f} {cur}</b>")
        else:
            lines.append("• Пока никто не отметил свои позиции — нажмите на блюда ниже!")
        if unclaimed_sum > 0:
            lines.append(f"• Не разобрано: <i>{unclaimed_sum:.2f} {cur}</i>")

    if not footer_free:
        lines.append(f"\n⚡ <i>Разделено в @{bot_username}</i>")

    text = "\n".join(lines)
    return text[:4000]
