"""
🔧 НАСТРОЙКА ПОД ТЕМУ (ЗАМЕНИТЬ ПЕРЕМЕННЫЕ ПОД СВОЮ ПРЕДМЕТНУЮ ОБЛАСТЬ)
================================================================================
Примеры замены для разных тем:

=== КАФЕ/РЕСТОРАН ===
SUBJECT_NAME = "Система управления кафе"
ROLE_ADMIN = "admin"         # Администратор
ROLE_CREATOR = "waiter"      # Официант
ROLE_WORKER = "cook"         # Повар
ENTITY_NAME = "Order"        # Заказ
ITEM_NAME = "Dish"           # Блюдо

=== АВТОСЕРВИС ===
SUBJECT_NAME = "Автосервис"
ROLE_ADMIN = "admin"         # Мастер-приемщик
ROLE_CREATOR = "diagnost"    # Автодиагност
ROLE_WORKER = "mechanic"     # Автомеханик
ENTITY_NAME = "Ticket"       # Наряд-заказ
ITEM_NAME = "Part"           # Запчасть/Работа

=== ПОЛИКЛИНИКА ===
SUBJECT_NAME = "Поликлиника"
ROLE_ADMIN = "admin"         # Зав. отделением
ROLE_CREATOR = "doctor"      # Врач
ROLE_WORKER = "nurse"        # Медсестра/Лаборант
ENTITY_NAME = "Patient"      # Пациент/Талон
ITEM_NAME = "Service"        # Услуга/Процедура

=== СКЛАД ===
SUBJECT_NAME = "Склад"
ROLE_ADMIN = "admin"         # Зав. складом
ROLE_CREATOR = "clerk"       # Кладовщик
ROLE_WORKER = "loader"       # Грузчик
ENTITY_NAME = "Request"      # Заявка
ITEM_NAME = "Product"        # Товар
================================================================================
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Order, Item, Reference
from datetime import datetime
import os

# ==============================================================================
# 🔧 КОНФИГУРАЦИЯ - МЕНЯТЬ ТОЛЬКО ЭТИ ПЕРЕМЕННЫЕ ПОД СВОЮ ТЕМУ
# ==============================================================================
SUBJECT_NAME = "Система управления заказами"  # Название системы
ROLE_ADMIN = "admin"       # Роль администратора
ROLE_CREATOR = "creator"   # Роль создателя заказов (Официант/Диагност/Врач)
ROLE_WORKER = "worker"     # Роль исполнителя (Повар/Механик/Медсестра)

# Статусы заказа (можно переименовать под тему)
STATUS_NEW = "new"           # Новый
STATUS_ACCEPTED = "accepted" # Принят в работу
STATUS_IN_PROGRESS = "in_progress"  # В процессе
STATUS_READY = "ready"       # Готов

# ==============================================================================
# ПРИКЛАДНОЕ ПРИЛОЖЕНИЕ
# ==============================================================================

app = Flask(__name__)
app.config['SECRET_KEY'] = 'demo-exam-secret-key-2024'  # Для сессий
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:admin@localhost/demo_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя по ID для Flask-Login"""
    return User.query.get(int(user_id))


# ==============================================================================
# ДЕКОРАТОРЫ ДЛЯ ПРОВЕРКИ РОЛЕЙ
# ==============================================================================

def role_required(*roles):
    """Декоратор для проверки роли пользователя"""
    def decorator(f):
        def wrap(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if current_user.role not in roles:
                flash('Доступ запрещен. Недостаточно прав.', 'error')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        wrap.__name__ = f.__name__
        return wrap
    return decorator


# ==============================================================================
# ОСНОВНЫЕ МАРШРУТЫ
# ==============================================================================

@app.route('/')
def index():
    """Главная страница - редирект в зависимости от роли"""
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    
    if current_user.role == ROLE_ADMIN:
        return redirect(url_for('admin_panel'))
    elif current_user.role == ROLE_CREATOR:
        return redirect(url_for('creator_panel'))
    elif current_user.role == ROLE_WORKER:
        return redirect(url_for('worker_panel'))
    else:
        flash('Неизвестная роль пользователя', 'error')
        return redirect(url_for('logout'))


@app.route('/hash')
def hash_generator():
    """Страница генерации хеша пароля (без авторизации)"""
    password = request.args.get('password', '')
    hash_result = ''
    if password:
        hash_result = generate_password_hash(password)
    return render_template('hash.html', password=password, hash_result=hash_result)


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        login_input = request.form.get('login', '')
        password = request.form.get('password', '')
        
        user = User.query.filter_by(login=login_input).first()
        
        if user and check_password_hash(user.password_hash, password):
            if user.is_blocked:
                flash('Ваш аккаунт заблокирован. Обратитесь к администратору.', 'error')
                return render_template('login.html', subject_name=SUBJECT_NAME)
            
            login_user(user)
            flash(f'Добро пожаловать, {user.full_name}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неверный логин или пароль', 'error')
    
    return render_template('login.html', subject_name=SUBJECT_NAME)


@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('login'))


# ==============================================================================
# АДМИН ПАНЕЛЬ (ROLE_ADMIN)
# ==============================================================================

@app.route('/admin')
@login_required
@role_required(ROLE_ADMIN)
def admin_panel():
    """Панель администратора: пользователи и заказы"""
    users = User.query.all()
    orders = Order.query.order_by(Order.date_created.desc()).all()
    return render_template('admin.html', 
                         users=users, 
                         orders=orders,
                         subject_name=SUBJECT_NAME,
                         role_admin=ROLE_ADMIN,
                         role_creator=ROLE_CREATOR,
                         role_worker=ROLE_WORKER,
                         status_new=STATUS_NEW,
                         status_accepted=STATUS_ACCEPTED,
                         status_in_progress=STATUS_IN_PROGRESS,
                         status_ready=STATUS_READY)


@app.route('/admin/block_user/<int:user_id>')
@login_required
@role_required(ROLE_ADMIN)
def block_user(user_id):
    """Блокировка пользователя"""
    user = User.query.get_or_404(user_id)
    user.is_blocked = not user.is_blocked
    db.session.commit()
    
    action = "заблокирован" if user.is_blocked else "разблокирован"
    flash(f'Пользователь {user.login} {action}', 'success')
    return redirect(url_for('admin_panel'))


@app.route('/admin/delete_order/<int:order_id>')
@login_required
@role_required(ROLE_ADMIN)
def delete_order(order_id):
    """Удаление заказа"""
    order = Order.query.get_or_404(order_id)
    db.session.delete(order)
    db.session.commit()
    flash('Заказ удален', 'success')
    return redirect(url_for('admin_panel'))


# ==============================================================================
# ПАНЕЛЬ СОЗДАТЕЛЯ (ROLE_CREATOR) - Официант/Диагност/Врач
# ==============================================================================

@app.route('/creator')
@login_required
@role_required(ROLE_CREATOR)
def creator_panel():
    """Панель создателя заказов: список своих заказов и создание нового"""
    orders = Order.query.filter_by(author_id=current_user.id).order_by(Order.date_created.desc()).all()
    return render_template('role1.html',
                         orders=orders,
                         subject_name=SUBJECT_NAME,
                         role_name="Создатель",
                         status_new=STATUS_NEW,
                         status_accepted=STATUS_ACCEPTED,
                         status_in_progress=STATUS_IN_PROGRESS,
                         status_ready=STATUS_READY)


@app.route('/creator/new', methods=['GET', 'POST'])
@login_required
@role_required(ROLE_CREATOR)
def create_order():
    """Создание нового заказа"""
    if request.method == 'POST':
        title = request.form.get('title', '')
        description = request.form.get('description', '')
        
        if not title:
            flash('Название заказа обязательно', 'error')
            return redirect(url_for('create_order'))
        
        order = Order(
            title=title,
            description=description,
            status=STATUS_NEW,
            author_id=current_user.id
        )
        db.session.add(order)
        db.session.commit()
        
        # Добавление позиций заказа (если есть)
        item_names = request.form.getlist('item_name[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        
        for i, name in enumerate(item_names):
            if name:
                try:
                    qty = int(item_quantities[i]) if item_quantities[i] else 1
                    price = float(item_prices[i]) if item_prices[i] else 0.0
                except ValueError:
                    qty = 1
                    price = 0.0
                
                item = Item(
                    order_id=order.id,
                    name=name,
                    quantity=qty,
                    price=price,
                    total=qty * price
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Заказ создан успешно', 'success')
        return redirect(url_for('creator_panel'))
    
    return render_template('create_order.html', subject_name=SUBJECT_NAME)


@app.route('/creator/edit/<int:order_id>', methods=['GET', 'POST'])
@login_required
@role_required(ROLE_CREATOR)
def edit_order(order_id):
    """Редактирование заказа (только свои, статус new)"""
    order = Order.query.get_or_404(order_id)
    
    if order.author_id != current_user.id:
        flash('Можно редактировать только свои заказы', 'error')
        return redirect(url_for('creator_panel'))
    
    if order.status != STATUS_NEW:
        flash('Можно редактировать только заказы со статусом "Новый"', 'error')
        return redirect(url_for('creator_panel'))
    
    if request.method == 'POST':
        order.title = request.form.get('title', order.title)
        order.description = request.form.get('description', order.description)
        
        # Удаляем старые позиции
        Item.query.filter_by(order_id=order.id).delete()
        
        # Добавляем новые
        item_names = request.form.getlist('item_name[]')
        item_quantities = request.form.getlist('item_quantity[]')
        item_prices = request.form.getlist('item_price[]')
        
        for i, name in enumerate(item_names):
            if name:
                try:
                    qty = int(item_quantities[i]) if item_quantities[i] else 1
                    price = float(item_prices[i]) if item_prices[i] else 0.0
                except ValueError:
                    qty = 1
                    price = 0.0
                
                item = Item(
                    order_id=order.id,
                    name=name,
                    quantity=qty,
                    price=price,
                    total=qty * price
                )
                db.session.add(item)
        
        db.session.commit()
        flash('Заказ обновлен', 'success')
        return redirect(url_for('creator_panel'))
    
    return render_template('edit_order.html', order=order, subject_name=SUBJECT_NAME)


# ==============================================================================
# ПАНЕЛЬ ИСПОЛНИТЕЛЯ (ROLE_WORKER) - Повар/Механик/Медсестра
# ==============================================================================

@app.route('/worker')
@login_required
@role_required(ROLE_WORKER)
def worker_panel():
    """Панель исполнителя: заказы в работе"""
    # Показываем все заказы кроме ready и не свои (если нужно)
    orders = Order.query.filter(
        Order.status.in_([STATUS_NEW, STATUS_ACCEPTED, STATUS_IN_PROGRESS])
    ).order_by(Order.date_created.asc()).all()
    
    return render_template('role2.html',
                         orders=orders,
                         subject_name=SUBJECT_NAME,
                         role_name="Исполнитель",
                         status_new=STATUS_NEW,
                         status_accepted=STATUS_ACCEPTED,
                         status_in_progress=STATUS_IN_PROGRESS,
                         status_ready=STATUS_READY)


@app.route('/worker/accept/<int:order_id>')
@login_required
@role_required(ROLE_WORKER)
def accept_order(order_id):
    """Принять заказ в работу"""
    order = Order.query.get_or_404(order_id)
    order.status = STATUS_IN_PROGRESS
    db.session.commit()
    flash(f'Заказ "{order.title}" принят в работу', 'success')
    return redirect(url_for('worker_panel'))


@app.route('/worker/complete/<int:order_id>')
@login_required
@role_required(ROLE_WORKER)
def complete_order(order_id):
    """Завершить заказ"""
    order = Order.query.get_or_404(order_id)
    order.status = STATUS_READY
    db.session.commit()
    flash(f'Заказ "{order.title}" выполнен', 'success')
    return redirect(url_for('worker_panel'))


# ==============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# ==============================================================================

if __name__ == '__main__':
    # Создание таблиц БД при первом запуске
    with app.app_context():
        db.create_all()
        print("=" * 60)
        print(f"🚀 {SUBJECT_NAME} запущена!")
        print("=" * 60)
        print(f"📊 База данных: mysql+pymysql://admin:admin@localhost/demo_db")
        print(f"👤 Роли: {ROLE_ADMIN}, {ROLE_CREATOR}, {ROLE_WORKER}")
        print(f"🔗 Генератор хеша: http://localhost:5000/hash")
        print("=" * 60)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
