from datetime import datetime
import os
from flask import Flask, redirect, render_template, request, session, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET_KEY", "jpstrezevo_secret_key_change_in_production"
)

# Database Configuration (Neon PostgreSQL with explicit psycopg2 driver & SSL support)
db_url = os.environ.get("DATABASE_URL")
if db_url:
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    if db_url.startswith("postgresql://") and "postgresql+psycopg2://" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    
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
    must_change_password = db.Column(db.Boolean, default=False)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    assigned_by = db.Column(db.String(80), nullable=False)
    assigned_to_manager = db.Column(db.String(80), nullable=False)
    assigned_to_employee = db.Column(db.String(80), nullable=True)
    assigned_to_sector = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(30), default="Доделено")
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
                must_change_password=False,
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

    if user.must_change_password:
        return redirect(url_for("change_password"))

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
    return render_template(
        "index.html", 
        user=user, 
        tasks=tasks, 
        managers=managers
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session["username"] = user.username
            if user.must_change_password:
                return redirect(url_for("change_password"))
            return redirect(url_for("index"))
        else:
            error = "Невалидно корисничко име или лозинка."
            
    return render_template("login.html", error=error)


@app.route("/change_password", methods=["GET", "POST"])
def change_password():
    if "username" not in session:
        return redirect(url_for("login"))
    
    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        return redirect(url_for("login"))

    error = None
    if request.method == "POST":
        new_pass = request.form.get("new_password", "").strip()
        confirm_pass = request.form.get("confirm_password", "").strip()

        if not new_pass or len(new_pass) < 4:
            error = "Новата лозинка мора да содржи барем 4 карактери."
        elif new_pass != confirm_pass:
            error = "Лозинките не се совпаѓаат."
        else:
            user.password = new_pass
            user.must_change_password = False
            db.session.commit()
            return redirect(url_for("index"))

    return render_template("change_password.html", user=user, error=error)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        role = request.form.get("role", "employee")
        sector = request.form.get("sector", "").strip() or "Општ сектор"

        if User.query.filter_by(username=username).first():
            error = "Корисничкото име веќе постои."
        else:
            try:
                new_user = User(
                    username=username, password=password, role=role, sector=sector, must_change_password=False
                )
                db.session.add(new_user)
                db.session.commit()
                
                session["username"] = new_user.username
                return redirect(url_for("index"))
            except Exception as e:
                db.session.rollback()
                error = f"Грешка при регистрација: {str(e)}"

    return render_template("signup.html", error=error)


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
    assigned_employee = request.form.get("assigned_to_employee")

    if status:
        task.status = status
    if report_note:
        task.report_note = report_note
    if assigned_employee:
        task.assigned_to_employee = assigned_employee
        task.status = "Проследено"

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
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "123456").strip() or "123456"
        role = request.form.get("role", "employee").strip()
        sector = request.form.get("sector", "").strip() or "Централна управа"

        if username:
            existing_user = User.query.filter_by(username=username).first()
            if not existing_user:
                new_u = User(
                    username=username, 
                    password=password, 
                    role=role, 
                    sector=sector, 
                    must_change_password=True
                )
                db.session.add(new_u)
                db.session.commit()
        return redirect(url_for("admin_users"))

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
