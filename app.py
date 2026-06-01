from flask import Flask, request, redirect, url_for, session, render_template, jsonify
import requests
import json
import re
import pymysql


app = Flask(__name__)
app.secret_key = 'super_secret_key_gia'

# --- КОНФИГУРАЦИЯ БД ---
DB_CONFIG = {
    'host': '134.90.167.42',
    'port': 10306,
    'user': 'Schlegel',
    'password': '10_oSm',
    'database': 'project_Schlegel',
    'cursorclass': pymysql.cursors.DictCursor
}

def get_db():
    try:
        connection = pymysql.connect(**DB_CONFIG)
        return connection
    except Exception as e:
        print(f"Ошибка БД: {e}")
        return None

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    remaining_attempts = 3

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        captcha_solved = request.form.get('captcha_solved', '0')

        db = get_db()
        if not db:
            return render_template('login.html', error="Ошибка подключения к базе данных", remaining_attempts=remaining_attempts)

        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        # 1. Если уже заблокирован в БД
        if user and user['is_blocked']:
            error = "Вы заблокированы. Обратитесь к администратору"
            db.close()
            return render_template('login.html', error=error, remaining_attempts=0)

        # 2. Определяем неудачу
        is_failed = (captcha_solved != '1') or (not user) or (user['password'] != password)

        if is_failed:
            # Базовое сообщение об ошибке
            error = "Вы ввели неверный логин или пароль. Пожалуйста проверьте ещё раз введенные данные"
            
            if user:
                new_att = user['failed_attempts'] + 1
                cursor.execute("UPDATE users SET failed_attempts = %s WHERE username = %s", (new_att, username))
                
                # Если достигли лимита -> блокируем СРАЗУ и меняем сообщение
                if new_att >= 3:
                    cursor.execute("UPDATE users SET is_blocked = 1 WHERE username = %s", (username,))
                    error = "Вы заблокированы. Обратитесь к администратору"
                
                remaining_attempts = max(0, 3 - new_att)
                db.commit()
                
            db.close()
            return render_template('login.html', error=error, remaining_attempts=remaining_attempts)

        # 3. УСПЕШНЫЙ ВХОД
        cursor.execute("UPDATE users SET failed_attempts = 0 WHERE username = %s", (username,))
        db.commit()
        db.close()

        session.clear()
        session['user_id'] = user['id']
        session['role'] = user['role']
        session['full_name'] = user['full_name']

        if user:  # После успешного входа
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['full_name'] = user['full_name']
            
            # Автоматическая переадресация по ролям
            if user['role'] == 'diagnostician':
                return redirect(url_for('orders'))
            elif user['role'] == 'mechanic':
                return redirect(url_for('orders'))
            else:
                return redirect(url_for('dashboard'))  # Только receptionist идёт на dashboard
    
    return render_template('login.html', error=error, remaining_attempts=remaining_attempts)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', 
                         role=session.get('role'), 
                         full_name=session.get('full_name'))


# --- МАРШРУТЫ ДЛЯ СПИСКА СОТРУДНИКОВ ---
@app.route('/employees')
def employees():
    # Проверка: только для админа (receptionist)
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    # Выбираем всех, кроме текущего админа (по желанию) или всех
    cursor.execute("SELECT id, username, full_name, role, status, is_blocked FROM users")
    users = cursor.fetchall()
    db.close()
    
    return render_template('employees.html', users=users)

# --- МАРШРУТ ДОБАВЛЕНИЯ СОТРУДНИКА ---
@app.route('/employees/add', methods=['GET', 'POST'])
def add_employee():
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('dashboard'))
        
    error = None
    success = None
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role')
        
        if not username or not password or not full_name:
            error = "Заполните все поля!"
        else:
            db = get_db()
            cursor = db.cursor()
            
            # 1. Проверка на дубликат (требование ТЗ)
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                error = "Пользователь с таким логином уже существует!"
            else:
                # 2. Добавление
                # status='active', is_blocked=0 по умолчанию
                cursor.execute("""
                    INSERT INTO users (username, password, full_name, role, status, is_blocked, failed_attempts)
                    VALUES (%s, %s, %s, %s, 'active', 0, 0)
                """, (username, password, full_name, role))
                db.commit()
                db.close()
                return redirect(url_for('employees'))
            db.close()
            
    return render_template('add_employee.html', error=error)

# --- МАРШРУТ УВОЛЬНЕНИЯ (Смена статуса) ---
@app.route('/employees/fire/<int:user_id>')
def fire_employee(user_id):
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    # Устанавливаем статус 'fired'
    cursor.execute("UPDATE users SET status = 'fired' WHERE id = %s", (user_id,))
    db.commit()
    db.close()
    return redirect(url_for('employees'))

# --- МАРШРУТ РАЗБЛОКИРОВКИ (Если заблочили за пароли) ---
@app.route('/employees/unblock/<int:user_id>')
def unblock_employee(user_id):
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    # Сбрасываем блок и ошибки
    cursor.execute("UPDATE users SET is_blocked = 0, failed_attempts = 0 WHERE id = %s", (user_id,))
    db.commit()
    db.close()
    return redirect(url_for('employees'))

@app.route('/employees/rehire/<int:user_id>')
def rehire_employee(user_id):
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('dashboard'))
        
    db = get_db()
    cursor = db.cursor()
    # Возвращаем статус active
    cursor.execute("UPDATE users SET status = 'active' WHERE id = %s", (user_id,))
    db.commit()
    db.close()
    return redirect(url_for('employees'))


# --- МАРШРУТЫ ДЛЯ СМЕН ---
@app.route('/shifts')
def shifts():
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('dashboard'))

    db = get_db()
    cursor = db.cursor()
    
    # Выбираем смены и сразу подтягиваем ФИО сотрудников (JOIN)
    sql = """
        SELECT s.id, s.date, s.shift_type, 
               m.full_name as mechanic_name, 
               d.full_name as diagnostician_name
        FROM shifts s
        LEFT JOIN users m ON s.mechanic_id = m.id
        LEFT JOIN users d ON s.diagnostician_id = d.id
        ORDER BY s.date DESC
    """
    cursor.execute(sql)
    shifts_list = cursor.fetchall()
    
    # Для формы добавления: нужны списки активных сотрудников (кроме приёмщиков)
    cursor.execute("SELECT id, full_name, role FROM users WHERE status = 'active' AND role != 'receptionist' ORDER BY role")
    employees = cursor.fetchall()
    db.close()
    
    return render_template('shifts.html', shifts=shifts_list, employees=employees)

@app.route('/shifts/add', methods=['POST'])
def add_shift():
    if 'role' not in session or session['role'] != 'receptionist':
        return redirect(url_for('dashboard'))

    date = request.form.get('date')
    shift_type = request.form.get('shift_type')
    mechanic_id = request.form.get('mechanic_id')
    diagnostician_id = request.form.get('diagnostician_id')
    admin_id = session['user_id'] # Кто создал смену

    if not date or not mechanic_id or not diagnostician_id:
        return "Ошибка: заполните все поля!", 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO shifts (date, shift_type, admin_id, mechanic_id, diagnostician_id)
        VALUES (%s, %s, %s, %s, %s)
    """, (date, shift_type, admin_id, mechanic_id, diagnostician_id))
    db.commit()
    db.close()
    return redirect(url_for('shifts'))


# --- МАРШРУТЫ ЗАКАЗОВ ---
@app.route('/orders')
def orders():
    if 'user_id' not in session: return redirect(url_for('login'))
    role = session['role']
    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Базовый SQL с JOIN для имен сотрудников
    # Добавляем GROUP_CONCAT для сбора запчастей в одну строку (например: "Масло x2, Фильтр x1")
    base_sql = """
        SELECT o.id, o.client_name, o.car_element, o.damage_count, o.parts_fluids, o.status, o.shift_id,
               m.full_name as mech_name, 
               d.full_name as diag_name,
               GROUP_CONCAT(CONCAT(p.name, ' x', op.quantity) SEPARATOR ', ') as parts_list
        FROM orders o
        JOIN shifts s ON o.shift_id = s.id
        LEFT JOIN users m ON s.mechanic_id = m.id
        LEFT JOIN users d ON s.diagnostician_id = d.id
        LEFT JOIN order_parts op ON o.id = op.order_id
        LEFT JOIN parts_catalog p ON op.part_id = p.id
    """

    if role == 'receptionist':
        # Приёмщик видит всё, группируем по ID заказа, чтобы избежать дублей строк из-за JOIN запчастей
        sql = base_sql + " GROUP BY o.id ORDER BY o.created_at DESC"
        cursor.execute(sql)
        
    elif role == 'diagnostician':
        # Диагност видит заказы смен, где он работал
        sql = base_sql + " WHERE s.diagnostician_id = %s GROUP BY o.id ORDER BY o.created_at DESC"
        cursor.execute(sql, (user_id,))
        
    elif role == 'mechanic':
        # Механик видит заказы только за СЕГОДНЯШНЮЮ смену
        sql = base_sql + " WHERE s.mechanic_id = %s AND s.date = CURDATE() GROUP BY o.id ORDER BY o.created_at DESC"
        cursor.execute(sql, (user_id,))
    else:
        cursor.execute("SELECT * FROM orders WHERE 0=1")

    orders_list = cursor.fetchall()
    db.close()
    return render_template('orders.html', orders=orders_list, role=role)

@app.route('/orders/create', methods=['GET', 'POST'])
def create_order():
    if session.get('role') != 'diagnostician': return redirect(url_for('dashboard'))
    error = None
    
    # Для формы добавления нужно получить список запчастей
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name, price FROM parts_catalog WHERE is_available = 1")
    parts_list = cursor.fetchall()
    db.close()
    
    if request.method == 'POST':
        client = request.form.get('client_name', '').strip()
        element = request.form.get('car_element', '').strip()
        damages = int(request.form.get('damage_count', 1))
        comment = request.form.get('parts_fluids', '').strip()
        parts_str = request.form.get('selected_parts', '') # Строка вида "1:2,5:1"
        
        if not client or not element:
            error = "Заполните обязательные поля"
        else:
            db = get_db()
            cursor = db.cursor()
            
            # 1. Ищем смену диагноста на сегодня
            cursor.execute("""
                SELECT id FROM shifts 
                WHERE diagnostician_id = %s AND date = CURDATE()
            """, (session['user_id'],))
            current_shift = cursor.fetchone()
            
            if not current_shift:
                error = "У вас нет назначенной смены на сегодня!"
            else:
                shift_id = current_shift['id']
                
                # 2. Создаем заказ
                cursor.execute("""
                    INSERT INTO orders (client_name, car_element, damage_count, parts_fluids, status, shift_id)
                    VALUES (%s, %s, %s, %s, 'принят', %s)
                """, (client, element, damages, comment, shift_id))
                
                order_id = cursor.lastrowid
                
                # 3. Добавляем запчасти в order_parts
                if parts_str:
                    for item in parts_str.split(','):
                        if ':' in item:
                            part_id, qty = item.split(':')
                            cursor.execute("""
                                INSERT INTO order_parts (order_id, part_id, quantity)
                                VALUES (%s, %s, %s)
                            """, (order_id, int(part_id), int(qty)))
                            
                db.commit()
                db.close()
                return redirect(url_for('orders'))
            db.close()
            
    return render_template('create_order.html', error=error, parts=parts_list)

@app.route('/orders/status/<int:order_id>', methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    role = session['role']
    new_status = request.form.get('status')

    # Разрешаем смену статуса только по ролям
    allowed = False
    if role == 'diagnostician' and new_status == 'оплачен':
        allowed = True
    elif role == 'mechanic' and new_status in ['готовится', 'готов']:
        allowed = True

    if allowed:
        db = get_db()
        cursor = db.cursor()
        cursor.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
        db.commit()
        db.close()
    return redirect(url_for('orders'))


# --- УПРАВЛЕНИЕ СПРАВОЧНИКОМ ЗАПЧАСТЕЙ ---
@app.route('/parts')
def parts_list():
    if session.get('role') != 'receptionist': return redirect(url_for('dashboard'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM parts_catalog ORDER BY id DESC")
    parts = cursor.fetchall()
    db.close()
    return render_template('parts_list.html', parts=parts)

@app.route('/parts/add', methods=['GET', 'POST'])
def add_part():
    if session.get('role') != 'receptionist': return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = float(request.form.get('price', 0))
        part_type = request.form.get('part_type', 'detail')
        if not name:
            error = "Введите название детали/жидкости"
        else:
            db = get_db()
            cursor = db.cursor()
            cursor.execute("INSERT INTO parts_catalog (name, price, part_type) VALUES (%s, %s, %s)", 
                           (name, price, part_type))
            db.commit()
            db.close()
            return redirect(url_for('parts_list'))
    return render_template('parts_form.html', error=error, part=None)

@app.route('/parts/edit/<int:part_id>', methods=['GET', 'POST'])
def edit_part(part_id):
    if session.get('role') != 'receptionist': return redirect(url_for('dashboard'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM parts_catalog WHERE id = %s", (part_id,))
    part = cursor.fetchone()
    if not part: return redirect(url_for('parts_list'))

    error = None
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        price = float(request.form.get('price', 0))
        part_type = request.form.get('part_type', 'detail')
        if not name:
            error = "Введите название"
        else:
            cursor.execute("UPDATE parts_catalog SET name=%s, price=%s, part_type=%s WHERE id=%s", 
                           (name, price, part_type, part_id))
            db.commit()
            db.close()
            return redirect(url_for('parts_list'))
    db.close()
    return render_template('parts_form.html', error=error, part=part)

@app.route('/parts/delete/<int:part_id>')
def delete_part(part_id):
    if session.get('role') != 'receptionist': return redirect(url_for('dashboard'))
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM parts_catalog WHERE id = %s", (part_id,))
    db.commit()
    db.close()
    return redirect(url_for('parts_list'))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



# ─────────────────────────────────────────────────────────────
# 🌐 НАСТРОЙКИ API (для экзамена - копируем как есть)
# ─────────────────────────────────────────────────────────────
API_PRIMARY_URL = "http://prb.sylas.ru/TransferSimulator/fullName"
API_FALLBACK_URL = "http://prb.sylas.ru/TransferSimulator/"  # Эмулятор для Linux

def get_fullname_source_url(use_fallback=False):
    """Возвращает URL источника: основной или запасной"""
    return API_FALLBACK_URL if use_fallback else API_PRIMARY_URL

# ─────────────────────────────────────────────────────────────
# 📡 API МАРШРУТ: получение и проверка ФИО
# ─────────────────────────────────────────────────────────────
@app.route('/api/get-fullname')
def get_fullname_api():
    if 'user_id' not in session:
        return jsonify({
            'success': False, 
            'error_code': 'AUTH_401', 
            'error': 'Требуется авторизация'
        }), 401

    for attempt, use_fallback in enumerate([False, True], 1):
        source_url = get_fullname_source_url(use_fallback)
        source_name = "fallback" if use_fallback else "primary"
        
        try:
            response = requests.get(source_url, timeout=10)
            response.raise_for_status()
            
            # Проверяем, не пустой ли ответ
            if not response.text.strip():
                raise ValueError("Пустой ответ от сервера")
            
            # Пробуем распарсить JSON
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise ValueError(f"Сервер вернул не JSON. Ответ: {response.text[:200]}...") from e
            
            # Получаем ФИО (адаптивно под разные форматы)
            full_name_value = data.get('value', data.get('full_name', data.get('name', '')))
            verification = verify_fullname(full_name_value)
            
            return jsonify({
                'success': True,
                'data': data,
                'verification': verification,
                'source_used': source_name,
                'attempts': attempt
            })
            
        except requests.exceptions.ConnectionError as e:
            if attempt == 2:
                return jsonify({
                    'success': False,
                    'error_code': 'CONN_ERR_502',
                    'error': 'Не удалось подключиться к серверу API. Проверьте интернет-соединение.',
                    'source_used': source_name,
                    'attempts': attempt,
                    'debug': str(e)
                }), 502
            continue
                
        except requests.exceptions.Timeout as e:
            if attempt == 2:
                return jsonify({
                    'success': False,
                    'error_code': 'TIMEOUT_ERR_504',
                    'error': 'Превышено время ожидания ответа от сервера (10 сек).',
                    'source_used': source_name,
                    'attempts': attempt
                }), 504
            continue
                
        except requests.exceptions.HTTPError as e:
            if attempt == 2:
                status = e.response.status_code if e.response else 'Unknown'
                return jsonify({
                    'success': False,
                    'error_code': f'HTTP_ERR_{status}',
                    'error': f'Сервер вернул ошибку HTTP {status}',
                    'source_used': source_name,
                    'attempts': attempt
                }), 500
            continue
        
        except ValueError as e:
            # Ошибка парсинга JSON или пустой ответ
            if attempt == 2:
                return jsonify({
                    'success': False,
                    'error_code': 'PARSE_ERR_500',
                    'error': f'Ошибка обработки ответа: {str(e)}',
                    'source_used': source_name,
                    'attempts': attempt
                }), 500
            continue
                
        except Exception as e:
            if attempt == 2:
                return jsonify({
                    'success': False,
                    'error_code': 'UNKNOWN_ERR_500',
                    'error': f'Непредвиденная ошибка: {str(e)}',
                    'source_used': source_name,
                    'attempts': attempt
                }), 500
            continue
    
    return jsonify({'success': False, 'error_code': 'UNKNOWN_ERR_500', 'error': 'Неизвестная ошибка'}), 500


# ─────────────────────────────────────────────────────────────
# 🔍 ФУНКЦИЯ ПРОВЕРКИ ФИО (без изменений)
# ─────────────────────────────────────────────────────────────
def verify_fullname(full_name):
    """Валидация ФИО: формат, кириллица, заглавные буквы"""
    if not full_name or not isinstance(full_name, str):
        return {
            'received_data': False, 'format_check': False, 
            'cyrillic_check': False, 'capital_letters_check': False, 
            'is_valid': False, 'error': 'Данные не получены или имеют неверный тип'
        }
    
    clean_name = full_name.strip()
    parts = re.split(r'\s+', clean_name)
    
    format_check = len(parts) == 3
    cyrillic_regex = re.compile(r'^[а-яёА-ЯЁ\s\-]+$')
    cyrillic_check = bool(cyrillic_regex.match(clean_name))
    capital_letters_check = all(part and part[0] == part[0].upper() for part in parts)
    
    return {
        'received_data': True,
        'full_name': clean_name,
        'format_check': format_check,
        'cyrillic_check': cyrillic_check,
        'capital_letters_check': capital_letters_check,
        'parts': parts,
        'is_valid': format_check and cyrillic_check and capital_letters_check
    }

@app.route('/check-fio')
def check_fio_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('fullname_check.html')


if __name__ == '__main__':
    app.run(debug=True)