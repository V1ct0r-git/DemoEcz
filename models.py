"""
🔧 НАСТРОЙКА ПОД ТЕМУ (ЗАМЕНИТЬ ПЕРЕМЕННЫЕ ПОД СВОЮ ПРЕДМЕТНУЮ ОБЛАСТЬ)
================================================================================
Примеры замены:
  - SUBJECT_NAME = "Автосервис"
  - ROLE_CREATOR = "diagnost" (Автодиагност)
  - ROLE_WORKER = "mechanic" (Автомеханик)
  - ENTITY_NAME = "Order" -> "Ticket" (Наряд-заказ)
  - ITEM_NAME = "Item" -> "Part" (Запчасть/Работа)
================================================================================
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# 🔧 ЗАМЕНИ 'Order' на название главной сущности твоей темы (например, Ticket, Patient, Request)
# 🔧 ЗАМЕНИ 'Item' на название позиции в заказе (например, Part, Service, Product)

class User(db.Model):
    """Таблица пользователей"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin, creator, worker
    full_name = db.Column(db.String(100), nullable=False)
    is_blocked = db.Column(db.Boolean, default=False)
    
    # Связь с заказами (один ко многим)
    # 🔧 Если меняешь Order на что-то другое, поменяй и здесь
    orders_created = db.relationship('Order', backref='author', lazy=True, foreign_keys='Order.author_id')
    
    def __repr__(self):
        return f'<User {self.login}>'


class Order(db.Model):
    """
    🔧 ЗАМЕНИ 'Order' на название главной сущности
    Главная таблица сущности (Заказ / Наряд / Талон / Заявка)
    """
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)  # Название/номер заказа
    description = db.Column(db.Text, nullable=True)    # Описание проблемы/заказа
    status = db.Column(db.String(20), default='new')   # new, accepted, in_progress, ready
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Связь с позициями заказа (один ко многим)
    # 🔧 Если меняешь Item на что-то другое, поменяй и здесь
    items = db.relationship('Item', backref='order', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Order {self.title}>'


class Item(db.Model):
    """
    🔧 ЗАМЕНИ 'Item' на название позиции (Блюдо / Запчасть / Услуга / Товар)
    Позиции внутри заказа (состав заказа)
    """
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)  # Название позиции
    quantity = db.Column(db.Integer, default=1)       # Количество
    price = db.Column(db.Float, default=0.0)          # Цена за единицу
    total = db.Column(db.Float, default=0.0)          # Итого (quantity * price)
    
    def __repr__(self):
        return f'<Item {self.name}>'


class Reference(db.Model):
    """
    Справочник (опционально)
    Например: Меню блюд, Список запчастей, Виды услуг
    """
    __tablename__ = 'references'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # Тип справочника
    price = db.Column(db.Float, default=0.0)         # Базовая цена
    
    def __repr__(self):
        return f'<Reference {self.name}>'
