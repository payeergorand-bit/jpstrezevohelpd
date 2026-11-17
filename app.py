import os
import io
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Безбедно вчитување на библиотеките за извоз
try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    from docx import Document
except ImportError:
    Document = None

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

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
    status = db.Column(db.String(30), default='Доделено')
    report_note = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

with app.app_context():
    db.create_all()
    
    # Безбедно додавање/решавање на колоните во PostgreSQL
    try:
        connection = db.engine.raw_connection()
        cursor = connection.cursor()
        cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256) DEFAULT \'\';')
        cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS role VARCHAR(20) DEFAULT \'employee\';')
        cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS sector VARCHAR(100) DEFAULT \'Општ сектор\';')
        cursor.execute('ALTER TABLE "user" ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT TRUE;')
        cursor.execute('ALTER TABLE "user" ALTER COLUMN password DROP NOT NULL;')
        connection.commit()
        cursor.close()
        connection.close()
    except Exception as e:
        print("Migration note:", e)

    # Список на основни корисници кои се креираат само ако не постојат
    default_users = [
        {"username": "admin", "role": "admin", "sector": "Централна управа", "pwd": "123456", "force_change": False},
        {"username": "вера.бешлиевска", "role": "director", "sector": "Дирекција", "pwd": "123456", "force_change": False},
        {"username": "владимир.крстевски", "role": "manager", "sector": "Технички сектор", "pwd": "123456", "force_change": False},
        {"username": "васко.колевски", "role": "employee", "sector": "Технички сектор", "pwd": "123456", "force_change": False},
        {"username": "горан.димовски", "role": "employee", "sector": "Технички сектор", "pwd": "123456", "force_change": False}
    ]

    for u_data in default_users:
        existing = User.query.filter_by(username=u_data["username"]).first()
        if not existing:
            new_u = User(
                username=u_data["username"],
                password_hash=generate_password_hash(u_data["pwd"]),
                role=u_data["role"],
                sector=u_data["sector"],
                must_change_password=u_data["force_change"]
            )
            db.session.add(new_u)
        else:
            if not existing.password_hash:
                existing.password_hash = generate_password_hash(u_data["pwd"])
    
    db.session.commit()

# Помошна функција за извоз
def get_tasks_for_export(selected_date=None):
    if "username" not in session:
        return None
    user = User.query.filter_by(username=session["username"]).first()
    if not user or user.role.lower() not in ["admin", "director", "manager"]:
        return None

    query = Task.query
    if user.role.lower() in ["admin", "director"]:
        pass 
    elif user.role.lower() == "manager":
        query = query.filter(
            (Task.assigned_to_manager == user.username) |
            (Task.assigned_to_sector == user.sector)
        )

    if selected_date:
        try:
            date_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Task.created_at) == date_obj)
        except ValueError:
            pass

    return query.order_by(Task.created_at.desc()).all()

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

    selected_date = request.args.get("date")

    if user.role.lower() in ["director", "admin"]:
        query = Task.query
    elif user.role.lower() == "manager":
        query = Task.query.filter(
            (Task.assigned_to_manager == user.username) | 
            (Task.assigned_to_sector == user.sector)
        )
    else:
        query = Task.query.filter_by(assigned_to_employee=user.username)

    if selected_date:
        try:
            d_obj = datetime.strptime(selected_date, '%Y-%m-%d').date()
            query = query.filter(db.func.date(Task.created_at) == d_obj)
        except ValueError:
            pass

    tasks = query.order_by(Task.created_at.desc()).all()
    managers = User.query.filter(User.role.in_(["employee", "manager"])).all()
    all_users = User.query.all() if user.role.lower() == "admin" else []
    
    return render_template("index.html", user=user, tasks=tasks, managers=managers, all_users=all_users, selected_date=selected_date)

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

# Рута за додавање корисник (само за администратор)
@app.route("/add_user", methods=["POST"])
def add_user():
    if "username" not in session:
        return redirect(url_for("login"))
    admin_user = User.query.filter_by(username=session["username"]).first()
    if not admin_user or admin_user.role.lower() != "admin":
        flash("Немате администраторски права.", "danger")
        return redirect(url_for("index"))

    new_username = request.form.get("new_username")
    new_password = request.form.get("new_password")
    role = request.form.get("role")
    sector = request.form.get("sector")

    if not new_username or not new_password:
        flash("Внесете корисничко име и лозинка.", "warning")
        return redirect(url_for("index"))

    existing = User.query.filter_by(username=new_username).first()
    if existing:
        flash("Корисникот веќе постои.", "danger")
        return redirect(url_for("index"))

    user = User(
        username=new_username,
        password_hash=generate_password_hash(new_password),
        role=role,
        sector=sector,
        must_change_password=True
    )
    db.session.add(user)
    db.session.commit()
    flash(f"Корисникот {new_username} е успешно креиран.", "success")
    return redirect(url_for("index"))

# Рута за ресетирање лозинка од страна на администратор
@app.route("/reset_password/<int:user_id>", methods=["POST"])
def reset_password(user_id):
    if "username" not in session:
        return redirect(url_for("login"))
    admin_user = User.query.filter_by(username=session["username"]).first()
    if not admin_user or admin_user.role.lower() != "admin":
        flash("Немате администраторски права.", "danger")
        return redirect(url_for("index"))

    target_user = User.query.get_or_404(user_id)
    target_user.password_hash = generate_password_hash("123456")
    target_user.must_change_password = True
    db.session.commit()
    flash(f"Лозинката за корисникот {target_user.username} е ресетирана на '123456'.", "success")
    return redirect(url_for("index"))

@app.route("/add_task", methods=["POST"])
def add_task():
    if "username" not in session:
        return redirect(url_for("login"))
    
    user = User.query.filter_by(username=session["username"]).first()
    if user.role.lower() not in ["director", "admin", "manager"]:
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

# ИЗВОЗ ВО EXCEL
@app.route("/export/excel")
def export_excel():
    if not openpyxl:
        flash("Excel модулот не е достапен на серверот.", "danger")
        return redirect(url_for("index"))
        
    selected_date = request.args.get("date")
    tasks = get_tasks_for_export(selected_date)
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
            t.id, t.title, t.description or "", t.assigned_to_manager,
            t.assigned_to_sector, t.assigned_to_employee or "Недоделено",
            t.status, t.report_note or "",
            t.created_at.strftime('%d.%m.%Y %H:%M') if t.created_at else ""
        ])

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    filename = f"izvestaj_{selected_date}.xlsx" if selected_date else "jp_strezevo_zadachi.xlsx"
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name=filename)

# ИЗВОЗ ВО WORD
@app.route("/export/word")
def export_word():
    if not Document:
        flash("Word модулот не е достапен на серверот.", "danger")
        return redirect(url_for("index"))

    selected_date = request.args.get("date")
    tasks = get_tasks_for_export(selected_date)
    if tasks is None:
        flash("Немате дозвола за извоз на податоци.", "danger")
        return redirect(url_for("index"))

    doc = Document()
    title_suffix = f" за датум: {selected_date}" if selected_date else ""
    doc.add_heading(f"ЈП Стрежево Битола - Извештај за задачи{title_suffix}", level=1)
    
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
    filename = f"izvestaj_{selected_date}.docx" if selected_date else "jp_strezevo_zadachi.docx"
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document", as_attachment=True, download_name=filename)

# ИЗВОЗ ВО PDF
@app.route("/export/pdf")
def export_pdf():
    if not REPORTLAB_AVAILABLE:
        flash("PDF модулот не е достапен на серверот.", "danger")
        return redirect(url_for("index"))

    selected_date = request.args.get("date")
    tasks = get_tasks_for_export(selected_date)
    if tasks is None:
        flash("Немате дозвола за извоз на податоци.", "danger")
        return redirect(url_for("index"))

    output = io.BytesIO()
    doc = SimpleDocTemplate(output, pagesize=letter)
    styles = getSampleStyleSheet()

    font_name = "Helvetica"
    dejavu_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "static/fonts/DejaVuSans.ttf"
    ]
    for path in dejavu_paths:
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont("CustomCyrillic", path))
            font_name = "CustomCyrillic"
            break

    normal_style = ParagraphStyle("CyrillicNormal", parent=styles["Normal"], fontName=font_name, fontSize=10, leading=14)
    title_style = ParagraphStyle("CyrillicTitle", parent=styles["Title"], fontName=font_name, fontSize=14, leading=18)

    elements = []
    title_text = f"ЈП Стрежево - Извештај ({selected_date})" if selected_date else "ЈП Стрежево Битола - Извештај за задачи"
    elements.append(Paragraph(title_text, title_style))
    elements.append(Spacer(1, 10))

    for t in tasks:
        task_text = (
            f"<b>Наслов:</b> {t.title}<br/>"
            f"<b>Опис:</b> {t.description or 'Нема'}<br/>"
            f"<b>Раководител:</b> {t.assigned_to_manager} | <b>Сектор:</b> {t.assigned_to_sector}<br/>"
            f"<b>Вработен:</b> {t.assigned_to_employee or 'Недоделено'} | <b>Статус:</b> {t.status}<br/>"
            f"<b>Забелешка:</b> {t.report_note or '-'}<br/>"
            f"<i>Датум: {t.created_at.strftime('%d.%m.%Y %H:%M') if t.created_at else ''}</i><br/>" + "-"*50
        )
        elements.append(Paragraph(task_text, normal_style))
        elements.append(Spacer(1, 6))

    doc.build(elements)
    output.seek(0)
    filename = f"izvestaj_{selected_date}.pdf" if selected_date else "jp_strezevo_zadachi.pdf"
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name=filename)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
