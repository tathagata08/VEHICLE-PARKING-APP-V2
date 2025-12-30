from flask import request, jsonify
from . import controller_bp
from model import db, Admin, User,ReserveParkingSpot,Parkinglot,Parkingspot
import jwt
from datetime import datetime, timedelta
from functools import wraps
import math
from flask import current_app


# Secret key for JWT
JWT_SECRET = "your_admin_secret_key"  # Keep it different from user JWT
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 3600  # 1 hour


## -------------------  Admin JWT -------------------
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", None)
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing token"}), 401

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            request.admin_id = payload["admin_id"]  # store admin_id
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        return f(*args, **kwargs)
    return decorated


# ------------------- Admin Login -------------------
@controller_bp.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    aid = data.get('aid')
    password = data.get('password')

    admin = Admin.query.filter_by(aid=aid).first()
    if admin and admin.password == password:
        payload = {
            "admin_id": admin.aid,
            "exp": datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS)
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return jsonify({"message": "Admin login successful", "token": token}), 200

    return jsonify({"error": "Invalid credentials"}), 401


# ------------------- Admin Logout -------------------
@controller_bp.route('/admin/logout', methods=['POST'])
def admin_logout():
    # For JWT stateless auth, just let the front-end delete the token
    return jsonify({"message": "Logged out"}), 200


@controller_bp.route('/admin/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():

    # Fetch admin info
    admin = Admin.query.filter_by(aid=request.admin_id).first()
    if not admin:
        return jsonify({"error": "Admin not found"}), 404

    adminName = admin.first_name + " " + admin.last_name

    

    # Total registered users
    totalUsers = User.query.count()

    lots = Parkinglot.query.all()
    print([lot.lotid for lot in lots])
    totalLots = len(lots)


    # Active reservations (not released)
    activeReservations = ReserveParkingSpot.query.filter_by(released_at=None).count()

    # Recent 10 reservations
    recentQuery = ReserveParkingSpot.query.order_by(
        ReserveParkingSpot.reserved_at.desc()
    ).limit(10).all()

    recentReservations = []
    for r in recentQuery:
        recentReservations.append({
            "id": r.id,
            "uid": r.uid,
            "spot_id": r.spot_id,
            "lot_location": r.parking_lot.location if r.parking_lot else None,
            "vehicle_number": r.vehicle_number,
            "released_at": r.released_at.strftime("%Y-%m-%d %H:%M") if r.released_at else None
        })

    recentBookingsCount = len(recentReservations)

   
    return jsonify({
        "adminName": adminName,
        "totalUsers": totalUsers,
        "totalLots": totalLots,
        "activeReservations": activeReservations,
        "recentBookingsCount": recentBookingsCount,
        "recentReservations": recentReservations
    }), 200




# ------------------- List all users -------------------
@controller_bp.route('/admin/users', methods=['GET'])
@admin_required
def admin_list_users():
    users = User.query.all()
    user_list = [
        {
            "uid": u.uid,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "age": u.age,
            "mob_no": u.mob_no,
            "is_blocked": u.is_blocked
        }
        for u in users
    ]
    return jsonify(user_list)



# ------------------- Block / Unblock user -------------------
@controller_bp.route('/admin/user/<uid>/block', methods=['POST'])
@admin_required
def block_user(uid):
    data = request.get_json()
    password = data.get("password")

    # Get the admin who is logged in
    admin = Admin.query.get(request.admin_id)

    # ❗ Validate admin password
    if admin.password != password:
        return jsonify({"error": "Invalid admin password!"}), 403

    # Toggle user block
    user = User.query.get_or_404(uid)
    user.is_blocked = not user.is_blocked
    db.session.commit()

    return jsonify({"message": f"User {uid} {'blocked' if user.is_blocked else 'unblocked'}"})



@controller_bp.route("/admin/users", methods=["GET"])
@admin_required
def get_users():
    users = User.query.all()
    return jsonify({"users": [
        {"uid": u.uid, "first_name": u.first_name, "last_name": u.last_name, "age": u.age, "mob_no": u.mob_no, "is_blocked": u.is_blocked}
        for u in users
    ]})



# Edit user details
@controller_bp.route('/admin/user/<string:uid>', methods=['PUT'])
@admin_required
def edit_user(uid):
    user = User.query.get_or_404(uid)
    data = request.get_json()
    user.first_name = data.get("first_name", user.first_name)
    user.last_name = data.get("last_name", user.last_name)
    user.age = data.get("age", user.age)
    user.mob_no = data.get("mob_no", user.mob_no)
    db.session.commit()
    return jsonify({"message": f"User {uid} updated successfully"}), 200


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


from utils.redis_cache import clear_cache

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

    
    try:
        clear_cache("user_lots")
    except Exception as e:
        current_app.logger.error(f"Redis cache clear failed: {e}")

    return jsonify({"message": "Parking lot created successfully"}), 201


# Edit Parking Lot
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

    
    try:
        clear_cache("user_lots")
    except Exception as e:
        current_app.logger.error(f"Redis cache clear failed: {e}")

    return jsonify({"message": f"Parking lot {lotid} updated successfully"}), 200


# Delete Parking Lot
@controller_bp.route('/admin/parkinglots/<int:lotid>', methods=['DELETE'])
@admin_required
def delete_parking_lot(lotid):
    lot = Parkinglot.query.get_or_404(lotid)

    # Check if any slot in the lot is currently occupied (active reservation)
    active_reservations = ReserveParkingSpot.query.filter_by(lot_id=lotid, released_at=None).count()
    if active_reservations > 0:
        return jsonify({"error": "Cannot delete lot: Some slots are currently reserved"}), 400

    # Delete all slots first
    for spot in lot.parking_spot:
        db.session.delete(spot)

    # Delete the lot itself
    db.session.delete(lot)
    db.session.commit()

   
    try:
        clear_cache("user_lots")
    except Exception as e:
        current_app.logger.error(f"Redis cache clear failed: {e}")

    return jsonify({"message": f"Parking lot {lot.location} deleted successfully"}), 200

@controller_bp.route('/admin/parking_lot/<int:lotid>/pause', methods=['PUT'])
@admin_required
def toggle_parking_lot_pause(lotid):
    lot = Parkinglot.query.get_or_404(lotid)
    data = request.get_json()

    if "is_paused" in data:
        lot.is_paused = data["is_paused"]
    else:
        lot.is_paused = not lot.is_paused

    db.session.commit()

    status = "paused" if lot.is_paused else "active"

    # Clear cache here if using cached user views
    clear_cache(f"user_lots")  # example, adapt to your caching

    return jsonify({
        "message": f"Parking lot {lotid} is now {status}",
        "is_paused": lot.is_paused  # return updated state
    }), 200



@controller_bp.route('/admin/user/<string:uid>/history', methods=['GET'])
@admin_required
def admin_user_history(uid):
    # Fetch all bookings for the given user
    history = ReserveParkingSpot.query.filter_by(uid=uid).order_by(ReserveParkingSpot.reserved_at.desc()).all()

    result = []
    for r in history:
        if r.released_at:
            duration = r.released_at - r.reserved_at
            hours = math.ceil(duration.total_seconds() / 3600)
            total_cost = r.total_cost
        else:
            duration = None
            hours = None
            total_cost = None

        result.append({
            "id": r.id,
            "lot_id": r.lot_id,
            "spot_id": r.spot_id,
            "vehicle_number": r.vehicle_number,
            "reserved_at": r.reserved_at,
            "released_at": r.released_at,
            "hours": hours,
            "total_cost": total_cost
        })

    return jsonify({"history": result})

## ===========================FOR CHARTS=====================================
@controller_bp.route('/admin/stats/bookings_per_lot', methods=['GET'])
@admin_required
def bookings_per_lot():
    lots = Parkinglot.query.all()
    lot_names = [f"{lot.location} (LOT-{lot.lotid})" for lot in lots]
    bookings = []
    for lot in lots:
        count = ReserveParkingSpot.query.filter_by(lot_id=lot.lotid).count()
        bookings.append(count)
    return jsonify({"lots": lot_names, "bookings": bookings})


@controller_bp.route('/admin/stats/revenue_per_lot', methods=['GET'])
@admin_required
def revenue_per_lot():
    lots = Parkinglot.query.all()
    lot_names = [f"{lot.location} (LOT-{lot.lotid})" for lot in lots]
    revenues = []
    for lot in lots:
        revenue_sum = db.session.query(db.func.sum(ReserveParkingSpot.total_cost))\
            .filter(ReserveParkingSpot.lot_id == lot.lotid, ReserveParkingSpot.released_at != None).scalar() or 0
        revenues.append(float(revenue_sum))
    return jsonify({"lots": lot_names, "revenue": revenues})

@controller_bp.route('/admin/stats/bookings_per_user', methods=['GET'])
@admin_required
def bookings_per_user():
    users = User.query.all()
    user_ids = [u.uid for u in users]
    bookings = []
    for u in users:
        count = ReserveParkingSpot.query.filter_by(uid=u.uid).count()
        bookings.append(count)
    return jsonify({"users": user_ids, "bookings": bookings})


# ------------------- Celery Tasks -------------------
from utils.tasks import send_monthly_report, generate_csv_export

# Trigger monthly report for a user
@controller_bp.route('/admin/send_report/<uid>', methods=['POST'])
@admin_required
def trigger_monthly_report(uid):
    send_monthly_report.delay(uid)
    return jsonify({"status": "success", "message": f"Monthly report task triggered for user {uid}."})

# Trigger CSV export for a lot
@controller_bp.route('/admin/export_csv', methods=['POST'])
@admin_required
def trigger_csv_export():
    lot_id = request.json.get('lot_id')  # optional
    generate_csv_export.delay(lot_id)
    return jsonify({"status": "success", "message": f"CSV export task triggered for lot {lot_id}."})
