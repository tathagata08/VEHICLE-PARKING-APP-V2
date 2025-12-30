from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import re
from sqlalchemy.orm import validates

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'
    uid = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    mob_no = db.Column(db.Integer, nullable=True)
    email = db.Column(db.String, nullable=True)  #
    is_blocked = db.Column(db.Boolean, default=False)
    reservations = db.relationship('ReserveParkingSpot', back_populates='user', cascade="all, delete-orphan")


class Admin(db.Model):
    __tablename__ = 'admin'
    aid = db.Column(db.String, primary_key=True)
    password = db.Column(db.String, nullable=False)
    first_name = db.Column(db.String, nullable=False)
    last_name = db.Column(db.String, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    mob_no = db.Column(db.Integer, nullable=True)

class Parkinglot(db.Model):
    __tablename__ = 'parking_lot'
    lotid = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    pin = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    no_of_slot = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String)
    is_paused = db.Column(db.Boolean, default=False)
    parking_spot = db.relationship('Parkingspot', back_populates='parking_lot', cascade="all, delete-orphan")
    reservations = db.relationship('ReserveParkingSpot', back_populates='parking_lot', cascade="all, delete-orphan")

class Parkingspot(db.Model):
    __tablename__ = 'parking_spot'
    spotid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    lotid = db.Column(db.Integer, db.ForeignKey('parking_lot.lotid'), nullable=False)
    status = db.Column(db.Boolean, default=False)
    parking_lot = db.relationship('Parkinglot', back_populates='parking_spot')
    reservations = db.relationship('ReserveParkingSpot', back_populates='parking_spot', cascade="all, delete-orphan")

class ReserveParkingSpot(db.Model):
    __tablename__ = 'reserve_parking_spot'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    uid = db.Column(db.String, db.ForeignKey('user.uid'), nullable=False)
    lot_id = db.Column(db.Integer, db.ForeignKey('parking_lot.lotid'), nullable=False)
    spot_id = db.Column(db.Integer, db.ForeignKey('parking_spot.spotid'), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    reserved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    released_at = db.Column(db.DateTime, nullable=True)
    total_cost = db.Column(db.Integer, nullable=True)
    vehicle_number = db.Column(db.String(12), nullable=False)

    @validates('vehicle_number')
    def validate_vehicle_number(self, key, value):
        pattern = r'^[A-Z]{2}-\d{2}-[A-Z]{1}-\d{4}$'
        if not re.match(pattern, value.upper()):
            raise ValueError("Invalid vehicle number format: use XX-00-X-0000")
        return value.upper()

    user = db.relationship('User', back_populates='reservations')
    parking_lot = db.relationship('Parkinglot', back_populates='reservations')
    parking_spot = db.relationship('Parkingspot', back_populates='reservations')
