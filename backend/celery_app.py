from celery import Celery
from flask import Flask
from model import db
from flask_mail import Mail

def create_app():
    app = Flask(__name__)

    # ---- Flask Config ----
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../instance/parking.db'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # ---- MailHog Email Config ----
    
    app.config['MAIL_SERVER'] = 'localhost'
    app.config['MAIL_PORT'] = 1025
    app.config['MAIL_USE_TLS'] = False
    app.config['MAIL_USE_SSL'] = False
    app.config['MAIL_USERNAME'] = ''  
    app.config['MAIL_PASSWORD'] = ''  
    app.config['MAIL_DEFAULT_SENDER'] = 'no-reply@quickpark.local'

    db.init_app(app)
    Mail(app)

    return app


def make_celery(app):
    celery = Celery(
        app.import_name,
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0"
    )

    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)

    celery.Task = ContextTask
    return celery


flask_app = create_app()
celery = make_celery(flask_app)

from celery.schedules import crontab

celery.conf.beat_schedule = {
    'send-daily-reminders-every-morning': {
        'task': 'utils.tasks.send_daily_reminders',
        'schedule': crontab(hour=8, minute=0),  # 8 AM daily
    },
}


import utils.tasks
