"""Comprobante de venta en PDF real (WeasyPrint) — diseño premium de marca.

El Docker runtime ya trae las libs nativas de WeasyPrint (ver Dockerfile: pango,
cairo, gdk-pixbuf). El logo va embebido en base64 para no depender de red en
tiempo de request; las tipografías se cargan de Google Fonts (@import), con
fallback a sans-serif del sistema si no hay red saliente.
"""

from __future__ import annotations

import base64
import io

LOGO_PNG_B64 = (
    "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"
)

PAYMENT_STATUS_STYLES = {
    "Pagado": {"fg": "#085041", "bg": "#d7f3ec", "border": "#a8e2d1", "label": "PAGADO"},
    "Pendiente": {"fg": "#8a1c1c", "bg": "#fde3e1", "border": "#f6b8b3", "label": "PENDIENTE"},
    "Abono parcial": {
        "fg": "#8a5a09",
        "bg": "#fdedd0",
        "border": "#f6cf8a",
        "label": "ABONO PARCIAL",
    },
}

ORDER_STATUS_LABELS = {
    "confirmed": "Venta activa",
    "completed": "Completada",
    "cancelled": "Venta anulada",
}

_MESES_ES = {
    1: "enero",
    2: "febrero",
    3: "marzo",
    4: "abril",
    5: "mayo",
    6: "junio",
    7: "julio",
    8: "agosto",
    9: "septiembre",
    10: "octubre",
    11: "noviembre",
    12: "diciembre",
}


def _format_fecha_es(dt) -> str:
    """Formatea fecha en español sin depender del locale del proceso (no thread-safe cambiarlo)."""
    hora = dt.strftime("%I:%M %p").lstrip("0") or dt.strftime("%I:%M %p")
    return f"{dt.day} de {_MESES_ES[dt.month]} de {dt.year}, {hora}"


def _qr_data_uri(data: str) -> str:
    import qrcode

    img = qrcode.make(data, border=1, box_size=6)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _money(value) -> str:
    return f"${float(value):,.0f}".replace(",", ".")


def _compact_ref(sku: str) -> str:
    raw = (sku or "").strip()
    if not raw:
        return "—"
    if len(raw) <= 14:
        return raw.upper()
    safe = "".join(ch for ch in raw if ch.isalnum())
    return f"REF-{(safe or raw)[-6:].upper()}"


def render_invoice_html(*, order, customer_name: str, customer_doc: str) -> str:
    """Arma el HTML del comprobante a partir de una Order (con items/payments cargados)."""
    is_cancelled = order.status == "cancelled"
    pay_style = PAYMENT_STATUS_STYLES.get(
        order.payment_status,
        {"fg": "#57534e", "bg": "#f5f5f4", "border": "#e7e5e4", "label": order.payment_status},
    )
    order_status_label = ORDER_STATUS_LABELS.get(order.status, order.status)

    items_rows = ""
    for item in order.items:
        discount = float(item.discount)
        disc_html = f"-{_money(discount)}" if discount > 0 else "—"
        items_rows += f"""
        <tr>
          <td class="product-cell">
            <div class="product-name">{item.name_snapshot}</div>
            <span class="ref-chip">{_compact_ref(item.sku_snapshot or "")}</span>
          </td>
          <td class="num">{item.quantity}</td>
          <td class="num">{_money(item.unit_price)}</td>
          <td class="num discount">{disc_html}</td>
          <td class="num bold">{_money(item.line_total)}</td>
        </tr>"""

    payments_rows = ""
    for pay in order.payments:
        method = (pay.method or "").replace("_", " ").title()
        ref = f" · {pay.reference}" if pay.reference else ""
        payments_rows += f"""
        <div class="payment-row">
          <span>{method}{ref}</span>
          <span class="bold">{_money(pay.amount)}</span>
        </div>"""
    if not payments_rows:
        payments_rows = '<p class="muted-italic">Sin pagos registrados todavía</p>'

    change_given = float(order.paid_amount) - float(order.grand_total)
    change_html = (
        f'<div class="payment-row change"><span>Cambio entregado</span><span class="bold">{_money(change_given)}</span></div>'
        if change_given > 0
        else ""
    )

    balance_banner = ""
    if float(order.balance_due) > 0 and not is_cancelled:
        balance_banner = f"""
        <div class="balance-banner">
          <span>Saldo pendiente</span>
          <span class="balance-amount">{_money(order.balance_due)}</span>
        </div>"""

    stamp_html = ""
    if order.payment_status == "Pagado" and not is_cancelled:
        stamp_html = '<div class="stamp">PAGADO<span>Bigotes y Paticas</span></div>'
    elif is_cancelled:
        stamp_html = '<div class="stamp cancelled">ANULADA<span>Bigotes y Paticas</span></div>'

    qr = _qr_data_uri(
        "https://wa.me/573206876633?text="
        + "Hola%2C%20tengo%20una%20pregunta%20sobre%20mi%20compra"
    )

    notes_html = ""
    if order.notes:
        notes_html = f'<div class="notes"><strong>Notas:</strong> {order.notes}</div>'

    shipping_row = ""
    if float(order.shipping_total) > 0:
        shipping_row = (
            f'<tr><td>Domicilio</td><td class="num">{_money(order.shipping_total)}</td></tr>'
        )
    discount_row = ""
    if float(order.discount_total) > 0:
        discount_row = f'<tr><td class="discount-label">Descuentos</td><td class="num discount">-{_money(order.discount_total)}</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Comprobante {order.order_number}</title>
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

    @page {{
        size: letter;
        margin: 1.5cm 1.6cm 1.3cm;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
        font-size: 10.5pt;
        color: #292524;
        background: #ffffff;
    }}
    .brand-bar {{
        height: 6px;
        border-radius: 4px;
        background: linear-gradient(90deg, #0d4a45 0%, #187f77 55%, #f5a641 100%);
        margin-bottom: 18px;
    }}
    .header {{
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 20px;
    }}
    .brand-block {{ display: flex; align-items: center; gap: 12px; }}
    .brand-block img {{ width: 46px; height: 46px; border-radius: 12px; }}
    .brand-name {{
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 16pt;
        font-weight: 800;
        color: #0d4a45;
        letter-spacing: -0.01em;
    }}
    .brand-tagline {{ font-size: 8pt; color: #78716c; margin-top: 2px; }}
    .invoice-meta {{ text-align: right; }}
    .invoice-eyebrow {{
        font-size: 7.5pt;
        font-weight: 700;
        letter-spacing: 0.12em;
        text-transform: uppercase;
        color: #a8a29e;
    }}
    .invoice-number {{
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 20pt;
        font-weight: 800;
        color: #0d4a45;
        margin-top: 2px;
    }}
    .invoice-date {{ font-size: 8.5pt; color: #78716c; margin-top: 2px; }}
    .status-pill {{
        display: inline-block;
        margin-top: 6px;
        padding: 3px 12px;
        border-radius: 999px;
        font-size: 7.5pt;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        background: {pay_style['bg']};
        color: {pay_style['fg']};
        border: 1px solid {pay_style['border']};
    }}

    .meta-grid {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        margin-bottom: 18px;
    }}
    .meta-card {{
        background: #fafaf9;
        border: 1px solid #e7e5e4;
        border-radius: 12px;
        padding: 12px 14px;
    }}
    .meta-label {{
        font-size: 7.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #a8a29e;
        margin-bottom: 6px;
    }}
    .meta-value {{ font-size: 10.5pt; font-weight: 600; color: #1c1917; }}
    .meta-sub {{ font-size: 8.5pt; color: #78716c; margin-top: 1px; }}

    table {{ width: 100%; border-collapse: collapse; }}
    thead th {{
        background: #f0f9f7;
        color: #085041;
        font-size: 7.5pt;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 9px 10px;
        text-align: left;
        border-bottom: 2px solid #cbe9e6;
    }}
    thead th.num {{ text-align: right; }}
    td {{ padding: 9px 10px; border-bottom: 1px solid #f0efed; font-variant-numeric: tabular-nums; vertical-align: top; }}
    tbody tr:nth-child(even) {{ background: #fbfbfa; }}
    .num {{ text-align: right; }}
    .bold {{ font-weight: 700; }}
    .discount {{ color: #b45309; }}
    .discount-label {{ color: #b45309; }}
    .product-name {{ font-weight: 600; color: #1c1917; margin-bottom: 3px; }}
    .ref-chip {{
        display: inline-block;
        font-family: 'Inter', monospace;
        font-size: 7.5pt;
        font-weight: 600;
        color: #085041;
        background: #e1f5ee;
        border-radius: 999px;
        padding: 1px 8px;
    }}

    .summary-wrap {{
        position: relative;
        margin-top: 16px;
    }}
    .summary {{
        display: grid;
        grid-template-columns: 1fr 230px;
        gap: 18px;
        align-items: start;
    }}
    .payments-card {{
        position: relative;
        border: 1px solid #e7e5e4;
        border-radius: 12px;
        padding: 12px 14px;
        min-height: 70px;
        overflow: hidden;
    }}
    .payments-title {{
        font-size: 7.5pt;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #a8a29e;
        font-weight: 700;
        margin-bottom: 8px;
    }}
    .payment-row {{ display: flex; justify-content: space-between; padding: 3px 0; font-size: 9.5pt; }}
    .payment-row.change {{ color: #085041; border-top: 1px dashed #e7e5e4; margin-top: 4px; padding-top: 6px; }}
    .muted-italic {{ color: #a8a29e; font-size: 9pt; font-style: italic; }}
    .totals-card {{
        border: 1px solid #cbe9e6;
        border-radius: 12px;
        background: #f9fcfc;
        padding: 10px 14px;
    }}
    .totals-card table td {{ border: none; padding: 4px 0; font-size: 9.5pt; }}
    .totals-card .grand td {{
        font-size: 14pt;
        font-weight: 800;
        color: #0d4a45;
        border-top: 2px solid #187f77;
        padding-top: 8px;
    }}

    .stamp {{
        position: absolute;
        top: 50%;
        right: -18px;
        width: 84px;
        height: 84px;
        margin-top: -42px;
        border: 2px solid #187f77;
        border-radius: 50%;
        color: #187f77;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 800;
        font-size: 9.5pt;
        letter-spacing: 0.04em;
        transform: rotate(-11deg);
        opacity: 0.16;
        z-index: 0;
    }}
    .stamp span {{ font-size: 5pt; font-weight: 700; letter-spacing: 0.03em; margin-top: 2px; text-transform: uppercase; }}
    .stamp.cancelled {{ border-color: #b91c1c; color: #b91c1c; font-size: 9pt; }}
    .payments-title, .payment-row, .muted-italic {{ position: relative; z-index: 1; }}

    .balance-banner {{
        margin-top: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: #fdedd0;
        border: 1px solid #f6cf8a;
        border-radius: 12px;
        padding: 10px 16px;
        font-weight: 700;
        color: #8a5a09;
    }}
    .balance-amount {{ font-size: 13pt; }}

    .notes {{
        margin-top: 14px;
        border: 1px dashed #d6d3d1;
        border-radius: 10px;
        padding: 10px 14px;
        color: #44403c;
        font-size: 9pt;
        background: #fafaf9;
    }}

    .footer {{
        margin-top: 22px;
        padding-top: 14px;
        border-top: 1px solid #e7e5e4;
        display: flex;
        align-items: center;
        gap: 16px;
    }}
    .footer img {{ width: 56px; height: 56px; border-radius: 8px; }}
    .footer-text {{ flex: 1; font-size: 8pt; color: #78716c; line-height: 1.5; }}
    .footer-text strong {{ color: #44403c; }}
    .thanks {{
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 700;
        color: #0d4a45;
        font-size: 10pt;
        margin-bottom: 2px;
    }}
</style>
</head>
<body>
    <div class="brand-bar"></div>

    <div class="header">
        <div class="brand-block">
            <img src="data:image/png;base64,{LOGO_PNG_B64}" alt="Bigotes y Paticas" />
            <div>
                <div class="brand-name">Bigotes y Paticas</div>
                <div class="brand-tagline">Tienda de mascotas · Dosquebradas, Colombia</div>
            </div>
        </div>
        <div class="invoice-meta">
            <div class="invoice-eyebrow">Comprobante de venta</div>
            <div class="invoice-number">{order.order_number}</div>
            <div class="invoice-date">{_format_fecha_es(order.occurred_at)}</div>
            <span class="status-pill">{pay_style['label']}</span>
        </div>
    </div>

    <div class="meta-grid">
        <div class="meta-card">
            <div class="meta-label">Cliente</div>
            <div class="meta-value">{customer_name}</div>
            <div class="meta-sub">{customer_doc or "Consumidor final"}</div>
        </div>
        <div class="meta-card">
            <div class="meta-label">Canal · Estado</div>
            <div class="meta-value">{order.channel}</div>
            <div class="meta-sub">{order_status_label}</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Producto</th>
                <th class="num">Cant.</th>
                <th class="num">Precio</th>
                <th class="num">Dto.</th>
                <th class="num">Total</th>
            </tr>
        </thead>
        <tbody>{items_rows}</tbody>
    </table>

    <div class="summary-wrap">
        <div class="summary">
            <div class="payments-card">
                {stamp_html}
                <div class="payments-title">Pagos recibidos</div>
                {payments_rows}
                {change_html}
            </div>
            <div class="totals-card">
                <table>
                    <tr><td>Subtotal</td><td class="num">{_money(order.subtotal)}</td></tr>
                    {discount_row}
                    {shipping_row}
                    <tr class="grand"><td>Total</td><td class="num">{_money(order.grand_total)}</td></tr>
                </table>
            </div>
        </div>
    </div>

    {balance_banner}
    {notes_html}

    <div class="footer">
        <img src="{qr}" alt="WhatsApp" />
        <div class="footer-text">
            <p class="thanks">¡Gracias por tu compra!</p>
            <p>Escanea el código para escribirnos por WhatsApp si tienes alguna pregunta sobre tu pedido.</p>
            <p><strong>Mall Zamara Plaza, Local 2</strong> · 320 687 6633 · bigotesypaticasdosquebradas@gmail.com · @bigotesypaticas</p>
        </div>
    </div>
</body>
</html>"""


def generate_invoice_pdf(html: str) -> bytes:
    """Renderiza el HTML a PDF real usando WeasyPrint (libs nativas ya en el Dockerfile)."""
    from weasyprint import HTML

    return HTML(string=html).write_pdf()
