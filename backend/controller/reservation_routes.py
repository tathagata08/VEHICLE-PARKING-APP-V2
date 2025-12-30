'''from flask import request, jsonify, session
from . import controller_bp
from model import db, ReserveParkingSpot, Parkingspot, Parkinglot,User
from datetime import datetime
import math


from functools import wraps
from flask import request, jsonify
import jwt
from model import Admin

JWT_SECRET = "your_admin_secret_key"
JWT_ALGORITHM = "HS256"
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


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.admin_id = payload["admin_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated

MAX_ACTIVE_RESERVATIONS = 1
VEHICLE_PATTERN = r"^[A-Z]{2}-\d{2}-[A-Z]-\d{4}$"    # Example: WB-12-A-1234


# -------------------- RESERVE SPOT --------------------
@controller_bp.route('/reserve/<int:lotid>', methods=['POST'])
@token_required
def reserve_spot(current_user_uid, lotid):

    # 1️⃣ Get user
    user = User.query.get_or_404(current_user_uid)

    # Check if user is blocked
    if user.is_blocked:
        return jsonify({"error": "Your account is blocked. Contact admin."}), 403

    data = request.get_json()
    vehicle_number = data.get("vehicle_number", "").strip().upper()

    # Validate vehicle number
    if not re.match(VEHICLE_PATTERN, vehicle_number):
        return jsonify({"error": "Invalid vehicle format. Use: XX-00-X-0000"}), 400

    # 2️⃣ Check active reservation limit
    active_reservations = ReserveParkingSpot.query.filter(
        ReserveParkingSpot.uid == current_user_uid,
        ReserveParkingSpot.released_at.is_(None)
    ).count()

    if active_reservations >= MAX_ACTIVE_RESERVATIONS:
        return jsonify({"error": f"You can have only {MAX_ACTIVE_RESERVATIONS} active reservation."}), 400

    # 3️⃣ Find parking lot
    lot = Parkinglot.query.get_or_404(lotid)

    # Check if lot is paused
    if lot.is_paused:
        return jsonify({"error": "This parking lot is temporarily paused."}), 400

    # 4️⃣ Find an empty spot
    spot = Parkingspot.query.filter_by(lotid=lotid, status=False).first()
    if not spot:
        return jsonify({"error": "No available spots in this lot"}), 400

    # 5️⃣ Create the reservation
    reservation = ReserveParkingSpot(
        uid=current_user_uid,
        lot_id=lotid,
        spot_id=spot.spotid,
        price=lot.price,
        vehicle_number=vehicle_number
    )

    # Mark spot occupied
    spot.status = True

    db.session.add(reservation)
    db.session.commit()

    return jsonify({
        "message": f"Spot {spot.spotid} reserved successfully.",
        "reservation_id": reservation.id
    })
    


# -------------------- RELEASE SPOT --------------------
@controller_bp.route('/release/<int:reservation_id>', methods=['POST'])
@token_required
def release_spot(current_user_uid, reservation_id):

    reservation = ReserveParkingSpot.query.get_or_404(reservation_id)

    # Check ownership
    if reservation.uid != current_user_uid:
        return jsonify({"error": "You cannot release someone else's reservation."}), 403

    # Already released?
    if reservation.released_at:
        return jsonify({"message": "Spot already released"}), 400

    # Release
    reservation.released_at = datetime.utcnow()

    # Free the spot
    spot = Parkingspot.query.get(reservation.spot_id)
    if spot:
        spot.status = False

    db.session.commit()

    return jsonify({
        "message": f"Spot {reservation.spot_id} released successfully",
        "released_at": reservation.released_at
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
# -------------------- ADMIN ROUTES --------------------


@controller_bp.route('/admin/parkinglots', methods=['GET'])
@admin_required
def get_parking_lots():
    lots = Parkinglot.query.all()
    result = []

    for lot in lots:
        # Prepare slots info
        slots = [{"spotid": spot.spotid, "status": spot.status} for spot in lot.parking_spot]

        result.append({
            "lotid": lot.lotid,
            "location": lot.location,
            "address": lot.address,
            "pin": lot.pin,
            "no_of_slot": lot.no_of_slot,
            "price": lot.price,
            "slots": slots  # send slots array
        })

    return jsonify({"parkingLots": result}), 200


# Create new parking lot + slots
@controller_bp.route('/admin/parkinglots', methods=['POST'])
@admin_required
def create_parking_lot():
    data = request.get_json()
    location = data.get("location")
    address = data.get("address")
    pin = data.get("pin")
    no_of_slot = data.get("no_of_slot")
    price = data.get("price")

    if not all([location, address, pin, no_of_slot, price]):
        return jsonify({"error": "Missing fields"}), 400

    lot = Parkinglot(location=location, address=address, pin=pin, no_of_slot=no_of_slot, price=price)
    db.session.add(lot)
    db.session.commit()

    # Create slots automatically
    for _ in range(no_of_slot):
        spot = Parkingspot(lotid=lot.lotid, status=False)
        db.session.add(spot)
    db.session.commit()

    return jsonify({"message": "Parking lot created successfully"}), 201


# ------------------- Edit Parking Lot -------------------
@controller_bp.route('/admin/parking_lot/<int:lotid>', methods=['PUT'])
@admin_required
def edit_parking_lot(lotid):
    lot = Parkinglot.query.get_or_404(lotid)
    data = request.get_json()

    # Update fields if provided
    lot.location = data.get("location", lot.location)
    lot.address = data.get("address", lot.address)
    lot.pin = data.get("pin", lot.pin)
    lot.price = data.get("price", lot.price)
    lot.no_of_slot = data.get("no_of_slot", lot.no_of_slot)
    lot.description = data.get("description", lot.description)
    lot.is_paused = data.get("is_paused", lot.is_paused)

    db.session.commit()
    return jsonify({"message": f"Parking lot {lotid} updated successfully"}), 200


@controller_bp.route('/admin/parkinglots/<int:lotid>', methods=['DELETE'])
@admin_required
def delete_parking_lot(lotid):
    lot = Parkinglot.query.get_or_404(lotid)

    # Check if any slot in the lot is currently occupied (active reservation)
    active_reservations = ReserveParkingSpot.query.filter_by(lot_id=lotid, released_at=None).count()
    if active_reservations > 0:
        return jsonify({"error": "Cannot delete lot: Some slots are currently reserved"}), 400

    # Delete all slots first (cascade will remove them if defined in model)
    for spot in lot.parking_spot:
        db.session.delete(spot)

    # Delete the lot itself
    db.session.delete(lot)
    db.session.commit()

    return jsonify({"message": f"Parking lot {lot.location} deleted successfully"}), 200'''
