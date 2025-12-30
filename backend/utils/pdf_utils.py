from fpdf import FPDF
import os
from model import ReserveParkingSpot

def generate_pdf_for_user(uid):
    reservations = ReserveParkingSpot.query.filter_by(uid=uid).order_by(
        ReserveParkingSpot.reserved_at.desc()
    ).all()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, f"Monthly Report for {uid}", ln=True)

    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Total Reservations: {len(reservations)}", ln=True)
    pdf.ln(5)

    for r in reservations:
        pdf.multi_cell(0, 8, f"Spot {r.spot_id} at Lot {r.lot_id}, Vehicle: {r.vehicle_number}, Reserved at: {r.reserved_at}")

    os.makedirs("exports", exist_ok=True)
    pdf_path = os.path.join("exports", f"user_{uid}_monthly_report.pdf")
    pdf.output(pdf_path)

    return pdf_path
