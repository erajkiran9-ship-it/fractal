"""
Creates a sample invoice PDF that can be dropped into data/incoming_invoices/
for testing the system.
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from pathlib import Path
import sys


def create_invoice_pdf(
    output_path: str,
    invoice_id: str = "INV-1006",
    customer_name: str = "FreshMart Grocers",
    customer_address: str = "456 Retail Ave, Milwaukee, WI 53202",
    contact_name: str = "Mary Johnson",
    issue_date: str = "2026-08-05",
    due_date: str = "2026-08-20",
    line_items: list = None,
    payment_terms: str = "Net 30",
):
    if line_items is None:
        line_items = [
            ("Organic Chips 12pk", 200, 45.00),
            ("Sparkling Water 24pk", 300, 38.00),
            ("Protein Bars 36pk", 150, 52.00),
            ("Granola Mix 20pk", 250, 42.00),
        ]

    doc = SimpleDocTemplate(output_path, pagesize=letter,
                           leftMargin=0.75*inch, rightMargin=0.75*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=24, textColor=colors.HexColor('#1a365d'))
    header_style = ParagraphStyle('Header', parent=styles['Normal'], fontSize=11, textColor=colors.HexColor('#4a5568'))
    bold_style = ParagraphStyle('Bold', parent=styles['Normal'], fontSize=11, fontName='Helvetica-Bold')

    elements = []

    # Company header
    elements.append(Paragraph("NutriCorp International", title_style))
    elements.append(Paragraph("123 Industrial Blvd, Chicago, IL 60601", header_style))
    elements.append(Paragraph("Phone: (312) 555-0100 | Email: billing@nutricorp.com", header_style))
    elements.append(Spacer(1, 30))

    # Invoice title
    elements.append(Paragraph(f"INVOICE", ParagraphStyle('InvTitle', parent=styles['Heading1'], fontSize=18)))
    elements.append(Spacer(1, 15))

    # Invoice details table
    invoice_info = [
        ["Invoice Number:", invoice_id, "Issue Date:", issue_date],
        ["Payment Terms:", payment_terms, "Due Date:", due_date],
    ]
    info_table = Table(invoice_info, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))

    # Bill To
    elements.append(Paragraph("Bill To:", bold_style))
    elements.append(Paragraph(customer_name, header_style))
    elements.append(Paragraph(customer_address, header_style))
    elements.append(Paragraph(f"Attn: {contact_name}", header_style))
    elements.append(Spacer(1, 25))

    # Line items
    table_data = [["Item", "Quantity", "Unit Price", "Total"]]
    subtotal = 0
    for item, qty, price in line_items:
        total = qty * price
        subtotal += total
        table_data.append([item, str(qty), f"${price:,.2f}", f"${total:,.2f}"])

    tax = subtotal * 0.05
    grand_total = subtotal + tax

    table_data.append(["", "", "Subtotal:", f"${subtotal:,.2f}"])
    table_data.append(["", "", "Tax (5%):", f"${tax:,.2f}"])
    table_data.append(["", "", "TOTAL:", f"${grand_total:,.2f}"])

    items_table = Table(table_data, colWidths=[3*inch, 1.2*inch, 1.3*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2d3748')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, len(line_items)), 0.5, colors.HexColor('#e2e8f0')),
        ('LINEBELOW', (2, -3), (-1, -3), 1, colors.HexColor('#4a5568')),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (2, -1), (-1, -1), 12),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 30))

    # Payment instructions
    elements.append(Paragraph("Payment Instructions:", bold_style))
    elements.append(Paragraph("Please remit payment to:", header_style))
    elements.append(Paragraph("Bank: First National Bank | Account: 98765-4321 | Routing: 071000013", header_style))
    elements.append(Paragraph(f"Reference: {invoice_id}", header_style))

    doc.build(elements)
    print(f"Invoice PDF created: {output_path}")
    print(f"  Invoice: {invoice_id}")
    print(f"  Customer: {customer_name}")
    print(f"  Amount: ${grand_total:,.2f}")
    print(f"  Due: {due_date}")


def main():
    base_dir = Path(__file__).parent.parent
    samples_dir = base_dir / "scripts" / "sample_invoices"
    samples_dir.mkdir(parents=True, exist_ok=True)

    # Create FreshMart invoice
    create_invoice_pdf(
        str(samples_dir / "freshmart_invoice.pdf"),
        invoice_id="INV-1006",
        customer_name="FreshMart Grocers",
        customer_address="456 Retail Ave, Milwaukee, WI 53202",
        contact_name="Mary Johnson",
        issue_date="2026-08-05",
        due_date="2026-08-20",
        line_items=[
            ("Organic Chips 12pk", 200, 45.00),
            ("Sparkling Water 24pk", 300, 38.00),
            ("Protein Bars 36pk", 150, 52.00),
            ("Granola Mix 20pk", 250, 42.00),
        ],
    )

    print()

    # Create MegaMart invoice
    create_invoice_pdf(
        str(samples_dir / "megamart_invoice.pdf"),
        invoice_id="INV-2006",
        customer_name="MegaMart Holdings",
        customer_address="789 Commerce Dr, New York, NY 10001",
        contact_name="Robert Chen",
        issue_date="2026-08-05",
        due_date="2026-09-19",
        payment_terms="Net 45",
        line_items=[
            ("Premium Snack Assortment", 500, 62.00),
            ("Organic Beverage Pack 48ct", 400, 85.00),
            ("Health Bar Variety 48pk", 350, 48.00),
            ("Sparkling Juice 12pk", 600, 35.00),
        ],
    )

    print()

    # Create QuickStop invoice
    create_invoice_pdf(
        str(samples_dir / "quickstop_invoice.pdf"),
        invoice_id="INV-3006",
        customer_name="QuickStop Convenience",
        customer_address="321 Main St, Detroit, MI 48201",
        contact_name="David Miller",
        issue_date="2026-08-05",
        due_date="2026-09-04",
        line_items=[
            ("Energy Drink 12pk", 100, 52.00),
            ("Trail Mix 24ct", 80, 38.00),
            ("Protein Shake 6pk", 120, 45.00),
            ("Granola Bars 36ct", 90, 42.00),
        ],
    )

    print()
    print("=" * 60)
    print("Sample invoices ready!")
    print(f"Copy a PDF to: data/incoming_invoices/")
    print(f"Then click 'Advance Day' on the Manager Dashboard.")


if __name__ == "__main__":
    main()
