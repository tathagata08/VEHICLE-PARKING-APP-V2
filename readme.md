# Vehicle Parking App - V2

This project is the **Vehicle Parking System (MAD-2 Project)** built using Flask (Backend), VueJS (Frontend), Bootstrap, SQLite, Redis, and Celery.

---

## 🚀 Tech Stack

* **Backend:** Flask (Blueprints, REST APIs)
* **Frontend:** Vue 3 (CDN-based), Bootstrap 5
* **Database:** SQLite
* **Caching:** Redis
* **Background Jobs:** Celery + Celery Beat
* **Email Testing:** MailHog (optional)

---

## 📁 Project Structure

```
MAD_2/
│── backend/
│   ├── app.py
│   ├── controller/
│   │   ├── __init__.py
│   │   ├── admin_routes.py
│   │   ├── user_routes.py
│   ├── models/
│   ├── utils/
│   ├── celery_app.py
│   └
│
│── frontend/
│   ├── index.html
│   ├── dashboard_admin.html
│   ├── dashboard_user.html
|   |__.....
|   |__.....
│   └── static/
│       ├
│       
│       
|___requirements.txt

---

## ⚙️ Setup Instructions

### 🔧 Requirements File

This project includes a **requirements.txt** file inside the backend folder. Install all dependencies using:

```sh
pip install -r requirements.txt
```

### 1️⃣ Backend Setup

```sh
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

Run Flask:

```sh
python app.py
```

### 2️⃣ Redis Setup

Install Redis (Windows WSL / Linux / Docker):

```sh
redis-server
```

### 3️⃣ Celery Worker:

```sh
celery -A celery_app.celery worker --loglevel=info --pool=solo
```

### 4️⃣ Celery Beat (Daily Reminder Scheduler)

````sh
celery -A celery_app.celery beat --loglevel=info
```sh
celery -A celery_app.celery worker --loglevel=info
````

### 4️⃣ Celery Beat (Scheduled Jobs)

```sh
celery -A celery_app.celery beat --loglevel=info
```

---

## 📧 MailHog Integration (Optional)

### Run MailHog

Docker:

```sh
docker run -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

SMTP config (Flask):

* Host: `localhost`
* Port: `1025`
* Email UI: `http://localhost:8025`

Celery tasks can send daily reminders & monthly reports.

---

## 🛠 Features

### 👨‍💼 Admin

* Add parking lots and parking spots
* View all reservations
* Manage users
* Scheduled daily & monthly report emails

### 👤 User

* Register/Login
* Reserve a parking spot
* View reservation status

---

## 🖼 Static Files Setup

Place images inside:

```
frontend/static/images/
```

Example usage inside Vue:

```html
<img src="static/images/car.png" />
```

---

## 🧪 Testing

* Use **MailHog** to test all outgoing emails.
* Use **Redis Monitor** for checking caching.
* Use **Celery logs** to verify scheduled tasks.

---

## 📝 Notes

* Always run Redis **before** Celery.
* Celery Beat must run in a separate terminal.
* Do not run backend from root folder; always: `cd backend && python app.py`.

---

