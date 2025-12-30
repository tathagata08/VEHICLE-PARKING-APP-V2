
from flask import Flask
from model import db 
from controller import controller_bp
from datetime import datetime

from flask_cors import CORS
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

app = Flask(__name__)
CORS(app, supports_credentials=True, origins=[
    "http://127.0.0.1:5500",  
    "http://localhost:5500",   
    "http://127.0.0.1:5000",  # 
    "http://127.0.0.1:5501"   #
])  

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/parking.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'helloworld'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = False 
app.config['SESSION_COOKIE_HTTPONLY'] = True

db.init_app(app)  
app.register_blueprint(controller_bp)

from database_seed import database_seed
from model import db, Admin 

with app.app_context():
    db.create_all()
    # Only seed if no Admin exists
    if not Admin.query.first():
        database_seed(app)


if __name__ == '__main__':
    app.run(debug=True)