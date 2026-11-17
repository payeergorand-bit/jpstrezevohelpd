<!DOCTYPE html>
<html lang="mk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JP Strezevo Bitola - HelpDesk</title>
    <!-- Bootstrap CSS CDN -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body class="bg-light">

    <!-- Gorna navigacioni lenta -->
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark mb-4">
        <div class="container-fluid">
            <a class="navbar-brand" href="{{ url_for('index') }}">ЈП Стрежево Битола - HelpDesk</a>
            <div class="d-flex align-items-center">
                <span class="text-light me-3">Dobredojdovte: <strong>{{ user.username }}</strong> (Uloga: {{ user.role }}, Sektor: {{ user.sector }})</span>
                
                <a href="{{ url_for('change_password') }}" class="btn btn-outline-warning btn-sm me-2">Promeni lozinka</a>
                <a href="{{ url_for('logout') }}" class="btn btn-outline-danger btn-sm">Odjava</a>
            </div>
        </div>
    </nav>

    <div class="container">

        <!-- Fles poraki -->
        {% with messages = get_flashed_messages(with_categories=true) %}
            {% if messages %}
                {% for category, message in messages %}
                    <div class="alert alert-{{ category }} alert-dismissible fade show" role="server">
                        {{ message }}
                        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                    </div>
                {% endfor %}
            {% endif %}
        {% endwith %}

        <!-- Filtriranje po datum i Izvoz -->
        <div class="card shadow-sm mb-4">
            <div class="card-body">
                <form method="GET" action="{{ url_for('index') }}" class="row g-3 align-items-center">
                    <div class="col-auto">
                        <label for="date" class="col-form-label"><strong>Filtriraj zadaci po datum:</strong></label>
                    </div>
                    <div class="col-auto">
                        <input type="date" id="date" name="date" class="form-control" value="{{ selected_date or '' }}">
                    </div>
                    <div class="col-auto">
                        <button type="submit" class="btn btn-primary">Filtriraj</button>
                        <a href="{{ url_for('index') }}" class="btn btn-secondary">Resetiraj</a>
                    </div>
                    
                    {% if user.role.lower() in ['admin', 'director', 'manager'] %}
                    <div class="col-auto ms-auto">
                        <span class="me-2 text-muted">Izvoz:</span>
                        <a href="{{ url_for('export_excel', date=selected_date) }}" class="btn btn-success btn-sm">Excel</a>
                        <a href="{{ url_for('export_word', date=selected_date) }}" class="btn btn-info btn-sm text-white">Word</a>
                        <a href="{{ url_for('export_pdf', date=selected_date) }}" class="btn btn-danger btn-sm">PDF</a>
                    </div>
                    {% endif %}
                </form>
            </div>
        </div>

        <!-- Administratorski panel: Dodaj korisnik, promena na uloga i resetiranje lozinki (Samo za admin) -->
        {% if user.role.lower() == 'admin' %}
        <div class="row mb-4">
            <!-- Forma za dodavanje nov korisnik -->
            <div class="col-md-5">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-secondary text-white"><strong>Dodaj nov korisnik</strong></div>
                    <div class="card-body">
                        <form method="POST" action="{{ url_for('add_user') }}">
                            <div class="mb-3">
                                <label class="form-label">Korisnicko ime:</label>
                                <input type="text" name="new_username" class="form-control" required placeholder="pr. ime.prezime">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Pocetna lozinka:</label>
                                <input type="text" name="new_password" class="form-control" required value="123456">
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Uloga:</label>
                                <select name="role" class="form-select" required>
                                    <option value="employee">Vraboten (employee)</option>
                                    <option value="manager">Rakovoditel (manager)</option>
                                    <option value="director">Direktor (director)</option>
                                    <option value="admin">Administrator (admin)</option>
                                </select>
                            </div>
                            <div class="mb-3">
                                <label class="form-label">Sektor:</label>
                                <input type="text" name="sector" class="form-control" placeholder="pr. Tehnicki sektor" required>
                            </div>
                            <button type="submit" class="btn btn-dark w-100">Kreiraj korisnik</button>
                        </form>
                    </div>
                </div>
            </div>

            <!-- Upravuvanje so korisnici, ulogi i resetiranje lozinki -->
            <div class="col-md-7">
                <div class="card shadow-sm h-100">
                    <div class="card-header bg-secondary text-white"><strong>Upravuvanje so korisnici, ulogi i lozinki</strong></div>
                    <div class="card-body table-responsive" style="max-height: 400px; overflow-y: auto;">
                        <table class="table table-sm table-striped align-middle">
                            <thead>
                                <tr>
                                    <th>Korisnik</th>
                                    <th>Uloga</th>
                                    <th>Akcija</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for u in all_users %}
                                <tr>
                                    <td>{{ u.username }}</td>
                                    <td>
                                        <form method="POST" action="{{ url_for('update_user_role', user_id=u.id) }}" class="d-flex align-items-center gap-1">
                                            <select name="new_role" class="form-select form-select-sm" style="width: 120px;">
                                                <option value="employee" {% if u.role == 'employee' %}selected{% endif %}>Vraboten</option>
                                                <option value="manager" {% if u.role == 'manager' %}selected{% endif %}>Rakovoditel</option>
                                                <option value="director" {% if u.role == 'director' %}selected{% endif %}>Direktor</option>
                                                <option value="admin" {% if u.role == 'admin' %}selected{% endif %}>Admin</option>
                                            </select>
                                            <button type="submit" class="btn btn-outline-primary btn-sm px-2">Zacuvaj</button>
                                        </form>
                                    </td>
                                    <td>
                                        <form method="POST" action="{{ url_for('reset_password', user_id=u.id) }}" style="display:inline;">
                                            <button type="submit" class="btn btn-warning btn-sm" onclick="return confirm('Dali ste sigurni deka sakate da ja resetirate lozinkata na ovoj korisnik na 123456?')">Resetiraj pass</button>
                                        </form>
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
        {% endif %}

        <!-- Forma za kreiranje nova zadaca -->
        {% if user.role.lower() in ['director', 'admin', 'manager'] %}
        <div class="card shadow-sm mb-4">
            <div class="card-header bg-primary text-white"><strong>Kreiraj nova zadaca</strong></div>
            <div class="card-body">
                <form method="POST" action="{{ url_for('add_task') }}">
                    <div class="mb-3">
                        <label for="title" class="form-label">Naslov na zadacata</label>
                        <input type="text" class="form-control" id="title" name="title" required>
                    </div>
                    <div class="mb-3">
                        <label for="description" class="form-label">Opis</label>
                        <textarea class="form-control" id="description" name="description" rows="3"></textarea>
                    </div>
                    <div class="mb-3">
                        <label for="manager_username" class="form-label">Izberi rakovoditel / vraboten za sektor</label>
                        <select class="form-select" id="manager_username" name="manager_username" required>
                            <option value="">-- Izberi od lista --</option>
                            {% for m in managers %}
                                <option value="{{ m.username }}">{{ m.username }} ({{ m.sector }} - {{ m.role }})</option>
                            {% endfor %}
                        </select>
                    </div>
                    <button type="submit" class="btn btn-success">Dodaj zadaca</button>
                </form>
            </div>
        </div>
        {% endif %}

        <!-- Lista na zadaci -->
        <div class="card shadow-sm mb-5">
            <div class="card-header bg-dark text-white"><strong>Lista na zadaci</strong></div>
            <div class="card-body">
                {% if tasks %}
                    <div class="table-responsive">
                        <table class="table table-bordered table-hover align-middle">
                            <thead class="table-light">
                                <tr>
                                    <th>ID</th>
                                    <th>Naslov / Opis</th>
                                    <th>Rakovoditel / Sektor</th>
                                    <th>Vraboten</th>
                                    <th>Status i Zabeleska</th>
                                    <th>Datum</th>
                                    <th>Akcii</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for task in tasks %}
                                <tr>
                                    <td>{{ task.id }}</td>
                                    <td>
                                        <strong>{{ task.title }}</strong><br>
                                        <small class="text-muted">{{ task.description or 'Nema opis' }}</small>
                                    </td>
                                    <td>
                                        {{ task.assigned_to_manager }}<br>
                                        <small class="badge bg-secondary">{{ task.assigned_to_sector }}</small>
                                    </td>
                                    <td>
                                        {{ task.assigned_to_employee or 'Nedodeleno' }}
                                    </td>
                                    <td>
                                        <form method="POST" action="{{ url_for('update_task', task_id=task.id) }}">
                                            <div class="mb-1">
                                                <select name="status" class="form-select form-select-sm">
                                                    <option value="Dodeleno" {% if task.status == 'Dodeleno' %}selected{% endif %}>Dodeleno</option>
                                                    <option value="Vo rabota" {% if task.status == 'Vo rabota' %}selected{% endif %}>Vo rabota</option>
                                                    <option value="Zavrseno" {% if task.status == 'Zavrseno' %}selected{% endif %}>Zavrseno</option>
                                                </select>
                                            </div>
                                            {% if user.role.lower() == 'employee' or user.role.lower() == 'manager' or user.role.lower() == 'admin' %}
                                            <div class="mb-1">
                                                <input type="text" name="assigned_to_employee" class="form-control form-control-sm" placeholder="Vnesete ime na vraboten" value="{{ task.assigned_to_employee or '' }}">
                                            </div>
                                            <div class="mb-1">
                                                <textarea name="report_note" class="form-control form-control-sm" placeholder="Izvestaj / Zabeleska...">{{ task.report_note or '' }}</textarea>
                                            </div>
                                            <button type="submit" class="btn btn-outline-primary btn-sm w-100">Zacuvaj</button>
                                            {% endif %}
                                        </form>
                                    </td>
                                    <td>
                                        <small>{{ task.created_at.strftime('%d.%m.%Y %H:%M') if task.created_at else '' }}</small>
                                    </td>
                                    <td>
                                        {% if task.report_note %}
                                            <span class="badge bg-success">Ima izvestaj</span>
                                        {% else %}
                                            <span class="badge bg-warning text-dark">Nema izvestaj</span>
                                        {% endif %}
                                    </td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                {% else %}
                    <p class="text-muted mb-0">Nema pronajdeni zadaci za prikazuvanje.</p>
                {% endif %}
            </div>
        </div>

    </div>

    <!-- Bootstrap JS Bundle CDN -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
