"""
create_sample_contract.py
--------------------------
Generates a realistic sample Software Services Agreement PDF
for testing the AI Contract Risk Analyzer.

Run: python create_sample_contract.py
Output: sample_contract.pdf (in project root)
"""

import fitz  # PyMuPDF


CONTRACT_TEXT = """
SOFTWARE SERVICES AGREEMENT

This Software Services Agreement ("Agreement") is entered into as of June 1, 2026,
by and between:

  Client:   TechStart Inc., a Delaware corporation ("Client")
  Vendor:   DevCorp Solutions Ltd., a UK private limited company ("Vendor")

================================================================================
1. SERVICES AND DELIVERABLES
================================================================================

Vendor agrees to design, develop, and deliver a custom inventory management
software platform ("Software") as detailed in Schedule A attached hereto.
Vendor shall commence work on June 15, 2026 and deliver the final product
no later than December 15, 2026.

================================================================================
2. PAYMENT TERMS
================================================================================

2.1  Client shall pay Vendor a total project fee of USD $120,000 (One Hundred
     Twenty Thousand Dollars), payable as follows:
       - 30% upfront upon signing: USD $36,000
       - 40% upon milestone completion: USD $48,000
       - 30% upon final delivery: USD $36,000

2.2  Invoices are due and payable within 60 days of receipt. Late payments shall
     accrue interest at the rate of 5% per month compounded daily.

2.3  Client shall bear all applicable taxes, duties, and levies.

================================================================================
3. TERMINATION
================================================================================

3.1  Either party may terminate this Agreement immediately at any time, for
     any reason or no reason, by providing written notice to the other party.

3.2  Upon termination, Client shall pay Vendor for all work completed up to
     the date of termination at Vendor's standard hourly rate of $250/hour.

3.3  Vendor reserves the right to suspend services without notice if any invoice
     remains unpaid beyond 7 days.

================================================================================
4. CONFIDENTIALITY
================================================================================

4.1  Each party agrees to hold the other's Confidential Information in strict
     confidence and not to disclose such information to any third party.

4.2  Confidential Information means any non-public technical, financial, or
     business information disclosed by either party.

4.3  These confidentiality obligations shall survive for 1 year following the
     termination of this Agreement.

================================================================================
5. INTELLECTUAL PROPERTY
================================================================================

5.1  All software, code, designs, and deliverables created under this Agreement
     shall remain the exclusive intellectual property of Vendor until full
     payment is received.

5.2  Upon receipt of final payment, Vendor grants Client a non-exclusive,
     non-transferable license to use the Software.

5.3  Client shall have no right to modify, reverse-engineer, sublicense, or
     resell the Software without Vendor's prior written consent.

================================================================================
6. GOVERNING LAW
================================================================================

This Agreement shall be governed by and construed in accordance with the laws
of England and Wales. Any disputes arising under this Agreement shall be
submitted exclusively to the courts of London, England.

================================================================================
7. ENTIRE AGREEMENT
================================================================================

This Agreement constitutes the entire agreement between the parties and
supersedes all prior negotiations, representations, or agreements. Any
modification must be in writing signed by both parties.


IN WITNESS WHEREOF, the parties have executed this Agreement as of the date
first written above.

TechStart Inc.                         DevCorp Solutions Ltd.
_______________________                _______________________
Name:  Sarah Johnson                   Name:  James Whitfield
Title: CEO                             Title: Managing Director
Date:  June 1, 2026                    Date:  June 1, 2026
"""


def create_pdf(output_path: str = "sample_contract.pdf"):
    doc = fitz.open()

    # --- Page 1 ---
    page = doc.new_page(width=595, height=842)  # A4

    # Header bar
    page.draw_rect(fitz.Rect(0, 0, 595, 60), color=(0.1, 0.2, 0.5), fill=(0.1, 0.2, 0.5))
    page.insert_text(
        fitz.Point(40, 38),
        "SOFTWARE SERVICES AGREEMENT",
        fontname="helv",
        fontsize=16,
        color=(1, 1, 1),
    )

    # Body text
    page.insert_textbox(
        fitz.Rect(40, 75, 555, 820),
        CONTRACT_TEXT.strip(),
        fontname="helv",
        fontsize=9.5,
        color=(0.1, 0.1, 0.1),
    )

    # Footer
    page.draw_line(fitz.Point(40, 815), fitz.Point(555, 815), color=(0.5, 0.5, 0.5))
    page.insert_text(
        fitz.Point(40, 828),
        "CONFIDENTIAL — AI Contract Risk Analyzer Sample Document   |   Page 1 of 1",
        fontname="helv",
        fontsize=7,
        color=(0.5, 0.5, 0.5),
    )

    doc.save(output_path)
    doc.close()
    print(f"\n✅ Sample contract created: {output_path}")
    print("   Upload this file to the AI Contract Risk Analyzer to test it!\n")
    print("   Expected detections:")
    print("   ✔ Payment Terms    — 60-day payment, 5%/month late fee (HIGH RISK)")
    print("   ✔ Termination      — Immediate termination, no notice period (HIGH RISK)")
    print("   ✔ Confidentiality  — Only 1-year survival clause (MEDIUM RISK)")
    print("   ✔ IP Ownership     — Vendor retains IP until full payment (HIGH RISK)")
    print("   ✔ Governing Law    — England & Wales")
    print("   ✘ Missing: Liability Limitation clause")
    print("   ✘ Missing: Indemnification clause")
    print("   ✘ Missing: Data Protection / GDPR clause\n")


if __name__ == "__main__":
    create_pdf("sample_contract.pdf")
