from celery_app import celery, create_app
from flask_mail import Message
from flask import current_app
from model import User, ReserveParkingSpot as Reservation
import pdfkit, csv, os
from io import StringIO
import datetime
import requests





app = create_app()


GCHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/XXXX/messages?key=YYY&token=ZZZ"

from celery import shared_task
import pdfkit, os, datetime

@shared_task
def send_monthly_report(uid):
    # Import inside the task to avoid circular imports
    from celery_app import create_app
    from model import User, ReserveParkingSpot as Reservation, ParkingLot
    from flask_mail import Message
    from flask import current_app

    app = create_app()

    with app.app_context():
        
        user = User.query.filter_by(uid=uid).first()
        if not user:
            return "User not found."

        # Last month
        today = datetime.date.today()
        first_day = today.replace(day=1) - datetime.timedelta(days=1)
        first_day = first_day.replace(day=1)
        last_day = today.replace(day=1) - datetime.timedelta(days=1)

        reservations = Reservation.query.filter(
            Reservation.uid == uid,
            Reservation.reserved_at >= datetime.datetime.combine(first_day, datetime.time.min),
            Reservation.reserved_at <= datetime.datetime.combine(last_day, datetime.time.max)
        ).all()

        total_reservations = len(reservations)

        lot_counts = {}
        for r in reservations:
            lot_counts[r.lot_id] = lot_counts.get(r.lot_id, 0) + 1

        most_used_lot_name = "N/A"
        if lot_counts:
            most_used_lot_id = max(lot_counts, key=lot_counts.get)
            lot = ParkingLot.query.get(most_used_lot_id)
            most_used_lot_name = lot.location if lot else str(most_used_lot_id)

        total_amount = sum(r.cost or 0 for r in reservations)

        html = f"<h2>Monthly Report - {first_day.strftime('%B %Y')}</h2>"
        html += f"<p>User: {user.first_name} {user.last_name} (UID: {user.uid})</p>"
        html += f"<p>Total Reservations: {total_reservations}</p>"
        html += f"<p>Most Used Lot: {most_used_lot_name}</p>"
        html += f"<p>Total Amount: ₹{total_amount}</p>"

        # Table
        html += "<table border='1' cellpadding='5'><tr><th>ID</th><th>Lot</th><th>Spot</th><th>Vehicle</th><th>Reserved At</th><th>Released At</th><th>Cost</th></tr>"
        for r in reservations:
            lot = ParkingLot.query.get(r.lot_id)
            html += f"<tr><td>{r.reservation_id}</td><td>{lot.location if lot else r.lot_id}</td><td>{r.spot_id}</td><td>{r.vehicle_number}</td><td>{r.reserved_at}</td><td>{r.released_at or 'Active'}</td><td>₹{r.cost or 0}</td></tr>"
        html += "</table>"

        # PDF path
        exports_path = os.path.join(os.getcwd(), "exports")
        os.makedirs(exports_path, exist_ok=True)
        pdf_path = os.path.join(exports_path, f"{user.uid}_monthly_report.pdf")
        pdfkit.from_string(html, pdf_path)

        # Send email
        mail = current_app.extensions['mail']
        msg = Message(
            subject=f"Monthly Report - {first_day.strftime('%B %Y')}",
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[user.email],
            body="Please find your monthly parking report attached."
        )
        with open(pdf_path, "rb") as f:
            msg.attach("monthly_report.pdf", "application/pdf", f.read())

        mail.send(msg)

    return f"Monthly report sent to {user.email}"


# ---------------- MONTHLY REPORT ----------------
@celery.task
def send_monthly_report(uid):
    with app.app_context():
        user = User.query.get(uid)
        if not user:
            return "User not found."

        reservations = Reservation.query.filter_by(uid=uid).all()

        html = f"<h3>Monthly Report for {user.first_name}</h3>"
        html += f"<p>Total Reservations: {len(reservations)}</p>"

        exports_path = os.path.join(os.getcwd(), "exports")
        os.makedirs(exports_path, exist_ok=True)

        pdf_path = os.path.join(exports_path, f"{user.uid}_monthly_report.pdf")

        
        wkhtmltopdf_path = r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe"
        config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
        pdfkit.from_string(html, pdf_path, configuration=config)

        mail = current_app.extensions['mail']
        msg = Message(
            subject="Your Monthly Report",
            sender=current_app.config['MAIL_USERNAME'],
            recipients=[user.email],
            body="Please find your monthly parking report attached."
        )

        with open(pdf_path, "rb") as f:
            msg.attach("monthly_report.pdf", "application/pdf", f.read())

        mail.send(msg)

    return "Monthly report sent."


# -- CSV EXPORT -----------
@celery.task
def generate_csv_export(lot_id=None):
    with app.app_context():

        exports_path = os.path.join(os.getcwd(), "exports")
        os.makedirs(exports_path, exist_ok=True)

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'ReservationID', 'UserID', 'LotID', 'SpotID',
            'VehicleNumber', 'ReservedAt', 'ReleasedAt'
        ])

        query = Reservation.query
        if lot_id:
            query = query.filter_by(lot_id=lot_id)

        for r in query.all():
            writer.writerow([
                r.id, r.uid, r.lot_id,
                r.spot_id, r.vehicle_number,
                r.reserved_at, r.released_at
            ])

        csv_path = os.path.join(exports_path, f"parking_export_{lot_id or 'all'}.csv")
        with open(csv_path, 'w') as f:
            f.write(output.getvalue())

    return csv_path
