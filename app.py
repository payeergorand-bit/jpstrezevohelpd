import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "strezevo_helpdesk_secret_key_2026")

# Подесување на базата на податоци (Neon PostgreSQL преку환경 DATABASE_URL, со fallback на локална SQLite)
database_url = os.environ.get("DATABASE_URL")
if database_url:
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///local_helpdesk.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

# Модел за Корисници
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, director, manager, employee
    sector = db.Column(db.String(100), nullable=True)
    must_change_password = db.Column(db.Boolean, default=True)

# Модел за Задачи
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assigned_by = db.Column(db.String(80), nullable=False)
    assigned_to_manager = db.Column(db.String(80), nullable=False)
    assigned_to_sector = db.Column(db.String(100), nullable=False)
    assigned_to_employee = db.Column(db.String(80), nullable=True)
    status = db.Column(db.String(30), default='Доделено')  # Доделено, Проследено, Во тек, Завршено
    report_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    # Креирање на почетен admin корисник ако не постои
    if not User.query.filter_by(username="admin").first():
        hashed_password = generate_password_hash("123456")
        admin_user = User(
            username="admin",
            password_hash=hashed_password,
            role="admin",
            sector="Централна управа",
            must_change_password=False
        )
        db.session.add(admin_user)
        db.session.commit()

@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        session.clear()
        return redirect(url_for("login"))

    if user.must_change_password:
        return redirect(url_for("change_password"))

    # Филтрирање на задачите според улогата на корисникот
    if user.role in ["director", "admin"]:
        tasks = Task.query.order_by(Task.created_at.desc()).all()
    elif user.role == "manager":
        tasks = Task.query.filter(
            (Task.assigned_to_manager == user.username) | 
            (Task.assigned_to_sector == user.sector)
        ).order_by(Task.created_at.desc()).all()
    else:
        tasks = Task.query.filter_by(assigned_to_employee=user.username).order_by(Task.created_at.desc()).all()

    managers = User.query.filter(User.role.in_(["employee", "manager"])).all()
    return render_template("index.html", user=user, tasks=tasks, managers=managers)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password_hash, password):
            session["username"] = user.username
            if user.must_change_password:
                return redirect(url_for("change_password"))
            return redirect(url_for("index"))
        flash("Невалидно корисничко име или лозинка.", "danger")
    return render_template("login.html")

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if "username" not in session:
        return redirect(url_for("login"))
    
    user = User.query.filter_by(username=session["username"]).first()
    if request.method == "POST":
        new_password = request.form.get("new_password")
        if new_password:
            user.password_hash = generate_password_hash(new_password)
            user.must_change_password = False
            db.session.commit()
            flash("Лозинката е успешно променета.", "success")
            return redirect(url_for("index"))
        flash("Внесете нова лозинка.", "warning")
    return render_template("change_password.html")

@app.route("/add_task", methods=["POST"])
def add_task():
    if "username" not in session:
        return redirect(url_for("login"))
    
    user = User.query.filter_by(username=session["username"]).first()
    if user.role not in ["director", "admin", "manager"]:
        return redirect(url_for("index"))

    title = request.form.get("title")
    description = request.form.get("description")
    manager_username = request.form.get("manager_username")

    manager_user = User.query.filter_by(username=manager_username).first()
    sector = manager_user.sector if manager_user else "Општ сектор"

    new_task = Task(
        title=title,
        description=description,
        assigned_by=user.username,
        assigned_to_manager=manager_username,
        assigned_to_sector=sector,
        status="Доделено"
    )
    db.session.add(new_task)
    db.session.commit()
    flash("Задачата е успешно креирана и доделена.", "success")
    return redirect(url_for("index"))

@app.route("/update_task/<int:task_id>", methods=["POST"])
def update_task(task_id):
    if "username" not in session:
        return redirect(url_for("login"))
    
    task = Task.query.get_or_404(task_id)
    new_status = request.form.get("status")
    assigned_to_employee = request.form.get("assigned_to_employee")
    report_note = request.form.get("report_note")

    if new_status:
        task.status = new_status
    if assigned_to_employee is not None:
        task.assigned_to_employee = assigned_to_employee
    if report_note is not None:
        task.report_note = report_note

    db.session.commit()
    flash("Задачата е успешно ажурирана.", "success")
    return redirect(url_for("index"))

@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if "username" not in session:
        return redirect(url_for("login"))
    
    current_user = User.query.filter_by(username=session["username"]).first()
    if current_user.role != "admin":
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        role = request.form.get("role")
        sector = request.form.get("sector")

        if User.query.filter_by(username=username).first():
            flash("Корисничкото име веќе постои.", "danger")
        else:
            default_password = generate_password_hash("123456")
            new_user = User(
                username=username,
                password_hash=default_password,
                role=role,
                sector=sector,
                must_change_password=True
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Корисникот е успешно креиран (привремена лозинка: 123456).", "success")
        return redirect(url_for("admin_users"))

    users = User.query.all()
    return render_template("admin_users.html", user=current_user, users=users)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
