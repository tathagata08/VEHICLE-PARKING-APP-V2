from flask import request, jsonify, current_app
from . import controller_bp
from model import db, User, ReserveParkingSpot,Parkinglot,Parkingspot
import jwt
from datetime import datetime, timedelta
import csv
from flask import  send_file, request
import os
from flask_cors import cross_origin


from utils.redis_cache import redis_client
import json




import math
from functools import wraps
import re

# JWT configuration
JWT_EXPIRATION_MINUTES = 60 


# Helper decorator 
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # JWT sent in Authorization header
        if 'Authorization' in request.headers:
            bearer = request.headers['Authorization']
            if bearer.startswith('Bearer '):
                token = bearer[7:]

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            current_user_uid = payload['uid']
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        return f(current_user_uid, *args, **kwargs)
    return decorated




# User signup

@controller_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    uid = data.get('uid')
    password = data.get('password')
    first_name = data.get('first_name')
    last_name = data.get('last_name')
    age = data.get('age')
    mob_no = data.get('mob_no')
    email = data.get('email')  # <-- NEW

    if User.query.filter_by(uid=uid).first():
        return jsonify({"error": "Username already taken"}), 400

    user = User(
        uid=uid,
        password=password,
        first_name=first_name,
        last_name=last_name,
        age=age,
        mob_no=mob_no,
        email=email  # <-- NEW
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "User created successfully"}), 201



# User login

@controller_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON data received"}), 400

    uid = data.get('uid')
    password = data.get('password')

    user = User.query.filter_by(uid=uid).first()
    if user and user.password == password:
        # Generate JWT
        payload = {
            "uid": user.uid,
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        }
        token = jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')

        return jsonify({
            "message": "Login successful",
            "token": token,
            "user": {
                "uid": user.uid,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "age": user.age,
                "mob_no": user.mob_no
            }
        }), 200

    return jsonify({"error": "Invalid credentials"}), 401


# Logout
# Update logged-in user's own profile
@controller_bp.route('/user/edit', methods=['GET', 'PUT'])
@token_required
def update_user(current_user_uid):
    user = User.query.get_or_404(current_user_uid)

    # GET -> return profile
    if request.method == 'GET':
        return jsonify({
            "user": {
                "uid": user.uid,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "age": user.age,
                "mob_no": user.mob_no
            }
        }), 200

    
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No JSON body provided"}), 400

    # update only provided fields (basic safety)
    if "first_name" in data:
        user.first_name = data.get("first_name") or user.first_name
    if "last_name" in data:
        user.last_name = data.get("last_name") or user.last_name
    if "age" in data:
        try:
            user.age = int(data.get("age", user.age))
        except (TypeError, ValueError):
            return jsonify({"error": "Invalid age"}), 400
    if "mob_no" in data:
        user.mob_no = data.get("mob_no", user.mob_no)

    db.session.commit()

    return jsonify({
        "message": "Profile updated successfully",
        "user": {
            "uid": user.uid,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "age": user.age,
            "mob_no": user.mob_no
        }
    }), 200



# User dashboard

@controller_bp.route('/dashboard', methods=['GET'])
@token_required
def user_dashboard(current_user_uid):
    uid = current_user_uid
    active = ReserveParkingSpot.query.filter_by(uid=uid, released_at=None).count()
    released = ReserveParkingSpot.query.filter(
        ReserveParkingSpot.uid == uid,
        ReserveParkingSpot.released_at.isnot(None)
    ).count()

    return jsonify({"active_reservations": active, "released_reservations": released})


@controller_bp.route('/user/active', methods=['GET'])
@token_required
def user_active_reservation(current_user_uid):
    active_reservations = ReserveParkingSpot.query.filter_by(
        uid=current_user_uid,
        released_at=None
    ).all()  # Get ALL non-released

    result = []
    for r in active_reservations:
        result.append({
            "reservation_id": r.id,
            "lot_id": r.lot_id,
            "spot_id": r.spot_id,
            "vehicle_number": r.vehicle_number,
            "reserved_at": r.reserved_at.isoformat()
        })

    return jsonify(result)

@controller_bp.route('/user/delete', methods=['DELETE'])
@token_required
def delete_user(current_user_uid):

    user = User.query.get_or_404(current_user_uid)

    # Prevent deletion if user has active reservation
    active = ReserveParkingSpot.query.filter_by(
        uid=current_user_uid, 
        released_at=None
    ).first()

    if active:
        return jsonify({"error": "Cannot delete account with active reservation"}), 400

    db.session.delete(user)
    db.session.commit()

    return jsonify({"message": "Account deleted"})

'''@controller_bp.route('/user/edit/profile', methods=['PUT'])
@token_required
def edit_user_profile(current_user_uid):

    user = User.query.get_or_404(current_user_uid)
    data = request.get_json()

    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.age = data.get("age", user.age)
    user.mob_no = data.get("mob_no", user.mob_no)

    db.session.commit()
    return jsonify({"message": "Profile updated successfully"})
'''
@controller_bp.route('/user/lots', methods=['GET'])
@token_required
def user_lot_list(current_user_uid):
    CACHE_KEY = "user_lots"

    
    try:
        cached = redis_client.get(CACHE_KEY)
        if cached:
            return jsonify(json.loads(cached)), 200
    except Exception as e:
        current_app.logger.error(f"Redis error: {e}")

    
    try:
        lots = Parkinglot.query.all()
        result = []
        for lot in lots:
            vacant = Parkingspot.query.filter_by(lotid=lot.lotid, status=False).count()
            result.append({
                "lot_id": lot.lotid,
                "location": lot.location,
                "vacant_spots": vacant,
                "price": lot.price,
                "is_paused": lot.is_paused
            })
    except Exception as e:
        current_app.logger.error(f"DB fetch error: {e}")
        return jsonify({"error": "Failed to fetch lots"}), 500

    
    try:
        redis_client.setex(CACHE_KEY, 60, json.dumps(result))  # TTL 60s
    except Exception as e:
        current_app.logger.error(f"Redis set error: {e}")

    return jsonify(result), 200


from utils.redis_cache import cache, clear_cache

from utils.redis_cache import cache, clear_cache

@controller_bp.route('/user/history', methods=['GET'])
@token_required
@cache(ttl=60)  # cache for 60 seconds
def user_history(current_user_uid):
    # Fetch all bookings for the user
    history = ReserveParkingSpot.query.filter(
        ReserveParkingSpot.uid == current_user_uid
    ).order_by(ReserveParkingSpot.reserved_at.desc()).all()

    result = []
    for r in history:
        if r.released_at:
            duration = r.released_at - r.reserved_at
            hours = math.ceil(duration.total_seconds() / 3600)
            total_cost = r.total_cost
        else:
            hours = None
            total_cost = None

        result.append({
            "id": r.id,
            "lot_id": r.lot_id,
            "spot_id": r.spot_id,
            "vehicle_number": r.vehicle_number,
            "reserved_at": r.reserved_at.isoformat(),
            "released_at": r.released_at.isoformat() if r.released_at else None,
            "hours": hours,
            "total_cost": total_cost
        })

    return {"history": result}  # return dict for caching






VEHICLE_PATTERN = r'^[a-z]{2}-\d{2}-[a-z]-\d{4}$'
MAX_ACTIVE_RESERVATIONS = 2  # adjust as needed

# -------------------- RESERVE SPOT --------------------
@controller_bp.route('/reserve/<int:lotid>', methods=['POST'])
@token_required
def reserve_spot(current_user_uid, lotid):

    
    user = User.query.get_or_404(current_user_uid)

    
    if user.is_blocked:
        return jsonify({"error": "Your account is blocked. Contact admin."}), 403

    
    data = request.get_json()
    vehicle_number = data.get("vehicle_number", "").strip()

   
    if not re.match(VEHICLE_PATTERN, vehicle_number, re.IGNORECASE):
        return jsonify({"error": "Invalid vehicle format. Use: XX-00-X-0000"}), 400

    
    active_reservations = ReserveParkingSpot.query.filter(
        ReserveParkingSpot.uid == current_user_uid,
        ReserveParkingSpot.released_at.is_(None)
    ).count()

    if active_reservations >= MAX_ACTIVE_RESERVATIONS:
        return jsonify({"error": f"You can have only {MAX_ACTIVE_RESERVATIONS} active reservation."}), 400

    
    lot = Parkinglot.query.get_or_404(lotid)

    
    if lot.is_paused:
        return jsonify({"error": "This parking lot is temporarily paused."}), 400

    spot = Parkingspot.query.filter_by(lotid=lotid, status=False).first()
    if not spot:
        return jsonify({"error": "No available spots in this lot"}), 400

    reservation = ReserveParkingSpot(
        uid=current_user_uid,
        lot_id=lotid,
        spot_id=spot.spotid,
        price=lot.price,
        vehicle_number=vehicle_number.upper()  # store in uppercase for consistency
    )

    
    spot.status = True

    db.session.add(reservation)
    db.session.commit()

    try:
        clear_cache(f"cache:user_history:{current_user_uid}*")
    except Exception as e:
        current_app.logger.error(f"Redis cache clear failed: {e}")

    return jsonify({
        "message": f"Spot {spot.spotid} reserved successfully.",
        "reservation_id": reservation.id
    })


from math import ceil
from datetime import datetime



@controller_bp.route('/release/<int:reservation_id>', methods=['POST'])
@token_required
def release_spot(current_user_uid, reservation_id):

    reservation = ReserveParkingSpot.query.get_or_404(reservation_id)

    if reservation.uid != current_user_uid:
        return jsonify({"error": "You cannot release someone else's reservation."}), 403

    if reservation.released_at:
        return jsonify({"message": "Spot already released"}), 400

    
    reservation.released_at = datetime.utcnow()

    
    spot = Parkingspot.query.get(reservation.spot_id)
    if spot:
        spot.status = False

    
    duration = reservation.released_at - reservation.reserved_at
    hours = ceil(duration.total_seconds() / 3600)
    reservation.total_cost = hours * reservation.price

    db.session.commit()
    try:
        clear_cache(f"cache:user_history:{current_user_uid}*")
    except Exception as e:
        current_app.logger.error(f"Redis cache clear failed: {e}")

    return jsonify({
        "message": f"Spot {reservation.spot_id} released successfully",
        "released_at": reservation.released_at,
        "total_cost": reservation.total_cost
    })


# -------------------- CALCULATE PAYMENT --------------------
@controller_bp.route('/payment/<int:reservation_id>', methods=['POST'])
@token_required
def calculate_payment(current_user_uid, reservation_id):

    reservation = ReserveParkingSpot.query.get_or_404(reservation_id)

    # Ensure reservation owner
    if reservation.uid != current_user_uid:
        return jsonify({"error": "Unauthorized"}), 403

    # Ensure spot is released first
    if not reservation.released_at:
        return jsonify({"error": "Please release the spot first"}), 400

    # Avoid double billing
    if reservation.total_cost is not None:
        return jsonify({
            "message": "Payment already calculated",
            "total_cost": reservation.total_cost
        })

    # Calculate duration in hours
    duration = reservation.released_at - reservation.reserved_at
    hours = math.ceil(duration.total_seconds() / 3600)
    
    reservation.total_cost = hours * reservation.price
    db.session.commit()

    return jsonify({
        "message": "Payment calculated successfully",
        "total_cost": reservation.total_cost,
        "hours": hours,
        "rate_per_hour": reservation.price
    })


import os
import csv
import math
from flask import request, jsonify, send_file, current_app
from . import controller_bp
from model import ReserveParkingSpot
from functools import wraps
from flask_cors import cross_origin  # for CORS


# Monthly report JSON route

@controller_bp.route("/user/monthly_report", methods=["GET"])
@token_required
def user_monthly_report(current_user_uid):
    uid = current_user_uid
    bookings = ReserveParkingSpot.query.filter_by(uid=uid).order_by(
        ReserveParkingSpot.reserved_at.desc()
    ).all()

    report = []
    for b in bookings:
        duration_hours = math.ceil((b.released_at - b.reserved_at).total_seconds() / 3600) if b.released_at else None
        total_cost = b.total_cost if b.released_at else None

        report.append({
            "reservation_id": b.id,
            "lot_id": b.lot_id,
            "spot_id": b.spot_id,
            "vehicle_number": b.vehicle_number,
            "reserved_at": b.reserved_at.isoformat() if b.reserved_at else None,
            "released_at": b.released_at.isoformat() if b.released_at else None,
            "duration_hours": duration_hours,
            "total_cost": total_cost
        })

    return jsonify({"monthly_report": report})



# CSV generator function

def generate_csv_for_user(uid):
    # Ensure exports folder exists
    export_dir = os.path.join(os.path.dirname(__file__), "exports")
    os.makedirs(export_dir, exist_ok=True)

    filepath = os.path.join(export_dir, f"user_{uid}_monthly_report.csv")

    bookings = ReserveParkingSpot.query.filter_by(uid=uid).order_by(
        ReserveParkingSpot.reserved_at.desc()
    ).all()

    with open(filepath, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Reservation ID", "Lot ID", "Spot ID", "Vehicle Number",
            "Reserved At", "Released At", "Duration Hours", "Total Cost"
        ])

        for b in bookings:
            reserved_at = b.reserved_at.isoformat() if b.reserved_at else ""
            released_at = b.released_at.isoformat() if b.released_at else ""
            duration_hours = math.ceil((b.released_at - b.reserved_at).total_seconds() / 3600) if b.released_at else ""
            total_cost = b.total_cost if b.released_at else ""

            writer.writerow([
                b.id,
                b.lot_id,
                b.spot_id,
                b.vehicle_number,
                reserved_at,
                released_at,
                duration_hours,
                total_cost
            ])

    return filepath



# CSV download route

from flask import make_response, request, send_file, current_app, jsonify
from flask_cors import cross_origin
import os
import pdfkit
from model import ReserveParkingSpot
from io import BytesIO

from fpdf import FPDF

@controller_bp.route('/user/monthly_report_csv', methods=['GET', 'OPTIONS'])
@cross_origin(origin='*', supports_credentials=True)
@token_required
def user_monthly_report_csv(current_user_uid=None):
   
    if request.method == 'OPTIONS':
        response = make_response('', 200)
        response.headers.add("Access-Control-Allow-Headers", "Authorization,Content-Type")
        response.headers.add("Access-Control-Allow-Methods", "GET,OPTIONS")
        response.headers.add("Access-Control-Allow-Origin", "*")
        return response

    # ---- GENERATE PDF ---
    try:
        reservations = ReserveParkingSpot.query.filter_by(uid=current_user_uid)\
            .order_by(ReserveParkingSpot.reserved_at.desc()).all()

        #  PDF in memory
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Monthly Report for {current_user_uid}", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.ln(10)
        pdf.cell(0, 10, f"Total Reservations: {len(reservations)}", ln=True)
        pdf.ln(5)

        for r in reservations:
            pdf.multi_cell(0, 8, f"Spot {r.spot_id} at Lot {r.lot_id}, Vehicle: {r.vehicle_number}, Reserved at: {r.reserved_at}")

        pdf_bytes = pdf.output(dest='S').encode('latin1')  
        

        # Send PDF to browser
        return send_file(
            BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=f"user_{current_user_uid}_monthly_report.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        current_app.logger.error(f"Error generating PDF for user {current_user_uid}: {e}")
        return jsonify({"error": f"Failed to generate PDF: {e}"}), 500