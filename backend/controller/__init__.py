from flask import Blueprint

controller_bp = Blueprint('controller', __name__)

from flask import Blueprint, jsonify

controller_bp = Blueprint('controller', __name__)

# Home route
@controller_bp.route('/')
def home():
    return jsonify({"message": "Welcome to Vehicle Parking System API - MAD-2!"})

# Import all other route modules
from . import user_routes
from . import admin_routes
from . import reservation_routes


from . import user_routes
from . import admin_routes
from . import reservation_routes
