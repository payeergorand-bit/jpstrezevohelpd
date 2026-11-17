import os
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import openpyxl
from docx import Document
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "strezevo_helpdesk_secret_key_2026")

# Подесување на базата на податоци (Neon PostgreSQL преку DATABASE_URL, со fallback на SQLite)
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

# Помошна функција за проверка на дозвола и филтрирање при извоз
def get_tasks_for_export():
    if "username" not in session:
        return None
    user = User.query.filter_by(username=session["username"]).first()
    if not user or user.role not in ["admin", "director", "manager"]:
        return None

    if user.role in ["admin", "director"]:
        return Task.query.order_by(Task.created_at.desc()).all()
    elif user.role == "manager":
        return Task.query.filter(
            (Task.assigned_to_manager == user.username) |
            (Task.assigned_to_sector == user.sector)
        ).order_by(Task.created_at.desc()).all()
    return []

# 1. ИЗВОЗ ВО EXCEL
@app.route("/export/excel")
def export_excel():
    tasks = get_tasks_for_export()
    if tasks is None:
        flash("Немате дозвола за извоз на податоци.", "danger")
        return redirect(url_for("index"))

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Задачи"

    headers = ["ID", "Наслов", "Опис", "Раководител", "Сектор", "Вработен", "Статус", "Забелешка", "Датум"]
    ws.append(headers)

    for cell in ws[1]:
        cell.font = openpyxl.styles.Font(bold=True)

    for t in tasks:
        ws.append([
            t.id,
            t.title,
            t.description or "",
            t.assigned_to_manager,
            t.assigned_to_sector,
            t.assigned_to_employee or "Недоделено",
            t.status,
            t.report_note or "",
            t.created_at.strftime('%d.%m.%Y %H:%M') if t.created_at else ""
        ])

    for col in ws.columns:
        max_length = 0
        column = col[0].column_letter
        for cell in col:
            val = str(cell.value or "")
            if len(val) > max_length:
                max_length = len(val)
        ws.column_dimensions[column].width = min(max_length + 4, 50)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name="jp_strezevo_zadachi.xlsx"
    )

# 2. ИЗВОЗ ВО WORD
@app.route("/export/word")
def export_word():
    tasks = get_tasks_for_export()
    if tasks is None:
        flash("Немате дозвола за извоз на податоци.", "danger")
        return redirect(url_for("index"))

    doc = Document()
    doc.add_heading("ЈП Стрежево Битола - Извештај за задачи", level=1)
    doc.add_paragraph(f"Генерирано на: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    for t in tasks:
        p = doc.add_paragraph(style='List Bullet')
        p.add_run(f"Наслов: {t.title}\n").bold = True
        p.add_run(f"Опис: {t.description or 'Нема опис'}\n")
        p.add_run(f"Раководител: {t.assigned_to_manager} | Сектор: {t.assigned_to_sector}\n")
        p.add_run(f"Вработен: {t.assigned_to_employee or 'Недоделено'} | Статус: {t.status}\n")
        if t.report_note:
            p.add_run(f"Забелешка: {t.report_note}\n")
        p.add_run(f"Датум: {t.created_at.strftime('%d.%m.%Y %H:%M') if t.created_at else ''}\n")
        doc.add_paragraph("-" * 40)

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        as_attachment=True,
        download_name="jp_strezevo_zadachi.docx"
    )

# 3. ИЗВОЗ ВО PDF
@app.route("/export/pdf")
def export_pdf():
    tasks = get_tasks_for_export()
    if tasks is None:
        flash("Немате дозвола за извоз на податоци.", "danger")
        return redirect(url_for("index"))

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()

    font_name = "Helvetica"
    dejavu_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "static/fonts/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf"
    ]
    for path in dejavu_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("CustomCyrillic", path))
            font_name = "CustomCyrillic"
            break

    title_style = ParagraphStyle(
        "CyrillicTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=16,
        leading=20
    )
    normal_style = ParagraphStyle(
        "CyrillicNormal",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14
    )

    elements = []
    elements.append(Paragraph("ЈП Стрежево Битола - Извештај за задачи", title_style))
    elements.append(Paragraph(f"Генерирано на: {datetime.now().strftime('%d.%m.%Y %H:%M')}", normal_style))
    elements.append(Spacer(1, 14))

    for t in tasks:
        task_text = (
            f"Наслов: {t.title}<br/>"
            f"Опис: {t.description or 'Нема опис'}<br/>"
            f"Раководител: {t.assigned_to_manager} | Сектор: {t.assigned_to_sector}<br/>"
            f"Вработен: {t.assigned_to_employee or 'Недоделено'} | Статус: {t.status}<br/>"
            f"Забелешка: {t.report_note or '-'}<br/>"
            f"Датум: {t.created_at.strftime('%d.%m.%Y %H:%M') if t.created_at else ''}<br/>"
            + "-" * 65
        )
        elements.append(Paragraph(task_text, normal_style))
        elements.append(Spacer(1, 8))

    doc.build(elements)
    output.seek(0)

    return send_file(
        output,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="jp_strezevo_zadachi.pdf"
    )

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
