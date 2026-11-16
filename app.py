from datetime import datetime
import os
from flask import Flask, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "jpstrezevo_secret_key_change_in_production"
)

# Database Configuration (Neon PostgreSQL with SSL support)
db_url = os.environ.get("DATABASE_URL")
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    if "sslmode" not in db_url:
        separator = "&" if "?" in db_url else "?"
        db_url = f"{db_url}{separator}sslmode=require"

app.config["SQLALCHEMY_DATABASE_URI"] = db_url or "sqlite:///local_helpdesk.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, director, manager, employee
    sector = db.Column(db.String(100), nullable=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assigned_by = db.Column(db.String(80), nullable=False)
    assigned_to_manager = db.Column(db.String(80), nullable=False)  # Корисничко име на задолжениот
    assigned_to_sector = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), default="Доделено")  # Доделено, Во тек, Завршено
    report_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# Initialize Database & Default Admin
with app.app_context():
    try:
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            admin_user = User(
                username="admin",
                password="adminpassword",
                role="admin",
                sector="Централна управа",
            )
            db.session.add(admin_user)
            db.session.commit()
    except Exception as e:
        print(f"Database init error: {e}")


# Routes
@app.route("/")
def index():
    if "username" not in session:
        return redirect(url_for("login"))

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        session.clear()
        return redirect(url_for("login"))

    # Приказ на задачи според улогата
    if user.role in ["director", "admin"]:
        tasks = Task.query.order_by(Task.created_at.desc()).all()
    elif user.role == "employee":
        tasks = Task.query.filter_by(assigned_to_manager=user.username).order_by(Task.created_at.desc()).all()
    else:  # Manager
        tasks = Task.query.filter_by(assigned_to_manager=user.username).order_by(Task.created_at.desc()).all()

    assignable_users = User.query.filter(User.role.in_(["employee", "manager"])).all()
    return render_template("index.html", user=user, tasks=tasks, managers=assignable_users)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["username"] = user.username
            return redirect(url_for("index"))
        return render_template("login.html", error="Невалидно корисничко име или лозинка.")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role", "employee")
        sector = request.form.get("sector") or "Општ сектор"

        if User.query.filter_by(username=username).first():
            return render_template("signup.html", error="Корисничкото име веќе постои.")

        try:
            new_user = User(
                username=username, password=password, role=role, sector=sector
            )
            db.session.add(new_user)
            db.session.commit()
            
            # Автоматска најава (сесија) веднаш по успешна регистрација
            session["username"] = new_user.username
            return redirect(url_for("index"))
        except Exception as e:
            db.session.rollback()
            return render_template("signup.html", error=f"Грешка при регистрација: {str(e)}")

    return render_template("signup.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/add_task", methods=["POST"])
def add_task():
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()
    if not user or user.role not in ["director", "admin", "manager"]:
        return redirect(url_for("index"))

    title = request.form.get("title")
    description = request.form.get("description")
    assigned_to_user = request.form.get("manager_username")

    target_user = User.query.filter_by(username=assigned_to_user).first()
    sector = target_user.sector if target_user else user.sector

    new_task = Task(
        title=title,
        description=description,
        assigned_by=user.username,
        assigned_to_manager=assigned_to_user,
        assigned_to_sector=sector,
    )
    db.session.add(new_task)
    db.session.commit()
    return redirect(url_for("index"))


@app.route("/update_task/<int:task_id>", methods=["POST"])
def update_task(task_id):
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()
    task = Task.query.get_or_404(task_id)

    status = request.form.get("status")
    report_note = request.form.get("report_note")

    task.status = status
    if report_note:
        task.report_note = report_note
    db.session.commit()

    return redirect(url_for("index"))


@app.route("/reports")
def reports():
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()

    if user.role in ["director", "admin"]:
        tasks = Task.query.order_by(Task.created_at.desc()).all()
    else:
        tasks = Task.query.filter_by(assigned_to_manager=user.username).all()

    return render_template("reports.html", user=user, tasks=tasks)


@app.route("/admin/users", methods=["GET", "POST"])
def admin_users():
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()
    if not user or user.role != "admin":
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        role = request.form.get("role")
        sector = request.form.get("sector") or "Општ сектор"

    users = User.query.all()
    return render_template("admin_users.html", user=user, users=users)


@app.route("/admin/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    if "username" not in session:
        return redirect(url_for("login"))
    user = User.query.filter_by(username=session["username"]).first()
    if not user or user.role != "admin":
        return redirect(url_for("index"))

    target_user = User.query.get_or_404(user_id)
    if target_user.username != "admin":
        db.session.delete(target_user)
        db.session.commit()
    return redirect(url_for("admin_users"))


if __name__ == "__main__":
    app.run(debug=True)
