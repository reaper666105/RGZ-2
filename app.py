from flask import Flask, url_for, render_template, redirect, session, request
from werkzeug.security import check_password_hash, generate_password_hash
from Db import db
from Db.models import hr_officers, employees
from flask_migrate import Migrate
from datetime import datetime


app = Flask(__name__)


app.secret_key = '1000mmr'
user_db = "zlyden"
host_ip = "127.0.0.1"
host_port = "5432"
database_name = "personnel"
password = "dota2"


app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{user_db}:{password}@{host_ip}:{host_port}/{database_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


db.init_app(app)

migrate = Migrate(app, db)


@app.route('/')
def start():
    return redirect(url_for('main'))


@app.route("/app/index", methods=['GET', 'POST'])
def main():
    username = session.get('username')

     # Получение параметров для поиска
    search_term = request.args.get('search', '')

    # Получение параметра для сортировки
    sort_by = request.args.get('sort', 'full_name')

    # Получение параметров для поиска
    search_term = request.args.get('search', '')

    # Получение номера страницы из параметра запроса
    page = int(request.args.get('page', 1))

    # Определение количества сотрудников на странице
    per_page = 20

    # Рассчет смещения для текущей страницы
    offset = (page - 1) * per_page

    # Запрос к базе данных для получения сотрудников для текущей страницы с учетом поиска
    employees_data = employees.query.filter(
        (employees.full_name.ilike(f'%{search_term}%')) |
        (employees.position.ilike(f'%{search_term}%')) |
        (employees.gender.ilike(f'%{search_term}%')) |
        (employees.phone.ilike(f'%{search_term}%')) |
        (employees.email.ilike(f'%{search_term}%')) |
        (employees.on_probation.is_(True) if search_term.lower() == 'да' else employees.on_probation.is_(False)) |  # Используем is_ для сравнения с BOOLEAN
        (employees.hire_date.cast(db.String).ilike(f'%{search_term}%'))  # Используем CAST для приведения типа hire_date к строке
    ).order_by(
         getattr(employees, sort_by)
    ).offset(offset).limit(per_page).all()

     # Получение общего количества сотрудников в таблице
    total_employees = employees.query.count()

    # Рассчет общего количества страниц
    total_pages = (total_employees + per_page - 1) // per_page

    return render_template('index.html', name=username, employees_data=employees_data, current_page=page, search_term=search_term, total_pages=total_pages)


@app.route('/app/register', methods=['GET', 'POST'])
def registerPage():
    errors = []

    if request.method == 'GET':
        return render_template("register.html", errors=errors)

    username = request.form.get("username")
    password = request.form.get("password")

    if not (username or password):
        errors.append("Пожалуйста, заполните все поля")
        print(errors)
        return render_template("register.html", errors=errors)
   
    existing_user = hr_officers.query.filter_by(username=username).first()

    if existing_user:
        errors.append('Пользователь с данным именем уже существует')
        return render_template('register.html', errors=errors, resultСur=existing_user)

    hashed_password = generate_password_hash(password)

    new_user = hr_officers(username=username, password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return redirect("/app/login")


@app.route('/app/login', methods=["GET", "POST"])
def loginPage():
    errors = []

    if request.method == 'GET':
        return render_template("login.html", errors=errors)

    username = request.form.get("username")
    password = request.form.get("password")

    if not (username or password):
        errors.append("Пожалуйста, заполните все поля")
        return render_template("login.html", errors=errors)

    user = hr_officers.query.filter_by(username=username).first()

    if user is None or not check_password_hash(user.password, password):
        errors.append('Неправильный пользователь или пароль')
        return render_template("login.html", errors=errors)

    session['id'] = user.id
    session['username'] = user.username

    return redirect("/app/index")


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('loginPage'))


@app.route('/app/new_employee', methods=['GET', 'POST'])
def create_employee():
    errors = []
    username = session.get('username')

    if username is None:
        errors.append('Пожалуйста, авторизуйтесь')
        return render_template('new_emp.html', errors=errors)

    if request.method == 'POST':
        full_name = request.form.get('full_name')
        position = request.form.get('position')
        gender = request.form.get('gender')
        phone = request.form.get('phone')
        email = request.form.get('email')
        on_probation = request.form.get('on_probation') == 'on'
        hire_date_str = request.form.get('hire_date')

        if not (full_name and position and gender and phone and email and hire_date_str):
            errors.append('Пожалуйста, заполните все обязательные поля')
            return render_template('new_emp.html', errors=errors)

        try:
            hire_date = datetime.strptime(hire_date_str, '%Y-%m-%d').date()
        except ValueError:
            errors.append('Неверный формат даты. Используйте YYYY-MM-DD.')
            return render_template('new_emp.html', errors=errors)

        new_employee = employees(
            full_name=full_name,
            position=position,
            gender=gender,
            phone=phone,
            email=email,
            on_probation=on_probation,
            hire_date=hire_date
        )

        db.session.add(new_employee)
        db.session.commit()

        return redirect(url_for('main'))

    return render_template('new_emp.html', errors=errors)


@app.route('/app/edit_employee/<int:employee_id>', methods=['GET', 'POST'])
def edit_employee(employee_id):
    errors = []
    username = session.get('username')

    if username is None:
        errors.append('Пожалуйста, авторизуйтесь')
        return render_template('edit_emp.html', errors=errors)

    employee = employees.query.get_or_404(employee_id)

    if request.method == 'POST':
        employee.full_name = request.form.get('full_name')
        employee.position = request.form.get('position')
        employee.gender = request.form.get('gender')
        employee.phone = request.form.get('phone')
        employee.email = request.form.get('email')
        employee.on_probation = request.form.get('on_probation') == 'on'
        employee.hire_date = datetime.strptime(request.form.get('hire_date'), '%Y-%m-%d').date()

        db.session.commit()

        return redirect(url_for('main'))

    return render_template('edit_emp.html', employee=employee, errors=errors)


@app.route('/app/delete_employee/<int:employee_id>', methods=['GET', 'POST'])
def delete_employee(employee_id):
    errors = []
    username = session.get('username')

    if username is None:
        errors.append('Пожалуйста, авторизуйтесь')
        return render_template('delete_emp.html', errors=errors)

    employee = employees.query.get_or_404(employee_id)

    db.session.delete(employee)
    db.session.commit()

    return redirect(url_for('main'))
