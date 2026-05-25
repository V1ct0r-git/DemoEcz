# 🚀 УНИВЕРСАЛЬНЫЙ ШАБЛОН Flask + MariaDB для демоэкзамена (09.02.07)

## 📋 Структура проекта

```
/workspace/
├── models.py           # Модели базы данных
├── app.py              # Основной файл приложения (маршруты, логика)
├── import_data.py      # Скрипт импорта данных из JSON/Excel
├── requirements.txt    # Зависимости Python
└── templates/
    ├── base.html       # Базовый шаблон с меню
    ├── login.html      # Страница входа
    ├── hash.html       # Генератор хеша пароля
    ├── admin.html      # Панель администратора
    ├── role1.html      # Панель создателя (Официант/Диагност)
    ├── role2.html      # Панель исполнителя (Повар/Механик)
    ├── create_order.html  # Создание заказа
    └── edit_order.html    # Редактирование заказа
```

---

## 🔧 БЫСТРАЯ АДАПТАЦИЯ ПОД ТЕМУ (5 минут)

### Шаг 1: Откройте `app.py` и найдите блок настроек (строки ~45-55)

```python
# 🔧 КОНФИГУРАЦИЯ - МЕНЯТЬ ТОЛЬКО ЭТИ ПЕРЕМЕННЫЕ ПОД СВОЮ ТЕМУ
SUBJECT_NAME = "Система управления заказами"  # Название системы
ROLE_ADMIN = "admin"       # Роль администратора
ROLE_CREATOR = "creator"   # Роль создателя заказов
ROLE_WORKER = "worker"     # Роль исполнителя
```

### Шаг 2: Замените под вашу тему

| Тема | SUBJECT_NAME | ROLE_CREATOR | ROLE_WORKER |
|------|--------------|--------------|-------------|
| **Кафе** | "Система управления кафе" | "waiter" | "cook" |
| **Автосервис** | "Автосервис" | "diagnost" | "mechanic" |
| **Поликлиника** | "Поликлиника" | "doctor" | "nurse" |
| **Склад** | "Склад" | "clerk" | "loader" |

### Шаг 3: Откройте `models.py` и замените названия сущностей

Найдите классы `Order` и `Item`. Если хотите, можете переименовать:
- `Order` → `Ticket` (Наряд-заказ), `Patient` (Пациент), `Request` (Заявка)
- `Item` → `Part` (Запчасть), `Dish` (Блюдо), `Service` (Услуга)

**Важно:** Меняйте название класса во всех файлах (`models.py`, `app.py`, `import_data.py`)!

---

## 📝 ИНСТРУКЦИЯ ПО ЗАПУСКУ

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Создание базы данных

1. Откройте phpMyAdmin (http://localhost/phpmyadmin)
2. Создайте новую базу данных с именем `demo_db`
3. Или выполните SQL:
```sql
CREATE DATABASE demo_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. Настройка пользователя БД (если нужно)

```sql
-- Создать пользователя (если не существует)
CREATE USER IF NOT EXISTS 'admin'@'localhost' IDENTIFIED BY 'admin';
GRANT ALL PRIVILEGES ON demo_db.* TO 'admin'@'localhost';
FLUSH PRIVILEGES;
```

### 4. Запуск приложения

```bash
python app.py
```

Приложение запустится на http://localhost:5000

### 5. Создание первого администратора

1. Откройте в браузере: http://localhost:5000/hash
2. Введите пароль (например, `admin123`)
3. Нажмите "Сгенерировать хеш"
4. Скопируйте полученный хеш
5. В phpMyAdmin выполните SQL:

```sql
INSERT INTO users (login, password_hash, role, full_name, is_blocked)
VALUES ('admin', 'scrypt:32768:8:1$...ВАШ_ХЕШ...', 'admin', 'Администратор', 0);

INSERT INTO users (login, password_hash, role, full_name, is_blocked)
VALUES ('creator', 'scrypt:32768:8:1$...ВАШ_ХЕШ...', 'creator', 'Иван Официантов', 0);

INSERT INTO users (login, password_hash, role, full_name, is_blocked)
VALUES ('worker', 'scrypt:32768:8:1$...ВАШ_ХЕШ...', 'worker', 'Петр Поваров', 0);
```

### 6. Вход в систему

1. Откройте http://localhost:5000/login
2. Логин: `admin`, Пароль: тот который вы хешировали
3. Готово! Вы в системе.

---

## 📊 ИМПОРТ ДАННЫХ

### Из JSON файла

Создайте файл `users.json`:
```json
[
    {
        "login": "user1",
        "full_name": "Иван Иванов",
        "role": "creator",
        "password_hash": "scrypt:32768:8:1$..."
    },
    {
        "login": "user2",
        "full_name": "Петр Петров",
        "role": "worker",
        "password_hash": "scrypt:32768:8:1$..."
    }
]
```

Запустите импорт:
```bash
python import_data.py --file users.json --type users
```

### Из Excel файла

Создайте файл `orders.xlsx` с колонками:
- A: title (название заказа)
- B: description (описание)
- C: status (статус, опционально)
- D: author_id (ID автора)

Запустите импорт:
```bash
python import_data.py --file orders.xlsx --type orders
```

### Режим предпросмотра

Чтобы посмотреть данные без сохранения:
```bash
python import_data.py --file data.json --type users --preview
```

---

## 🎯 РОЛИ И ФУНКЦИОНАЛ

### 👑 Администратор (admin)
- Просмотр всех пользователей
- Блокировка/разблокировка пользователей
- Просмотр всех заказов
- Удаление заказов

### 📝 Создатель (creator / waiter / diagnost / doctor)
- Создание новых заказов
- Добавление позиций в заказ
- Редактирование своих заказов (пока статус "Новый")
- Просмотр истории своих заказов

### 🔧 Исполнитель (worker / cook / mechanic / nurse)
- Просмотр всех активных заказов
- Принятие заказа в работу (статус → "В работе")
- Завершение заказа (статус → "Готов")

---

## 🔄 СТАТУСЫ ЗАКАЗОВ

| Статус | Код | Описание |
|--------|-----|----------|
| Новый | `new` | Заказ создан, ожидает обработки |
| Принят | `accepted` | Подтвержден (опционально) |
| В работе | `in_progress` | Исполнитель приступил к работе |
| Готов | `ready` | Заказ выполнен |

---

## 🛠️ НАСТРОЙКА БАЗЫ ДАННЫХ

Конфигурация подключения в `app.py`:
```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:admin@localhost/demo_db'
```

Измените при необходимости:
- `admin:admin` → `ваш_логин:ваш_пароль`
- `localhost` → IP сервера
- `demo_db` → имя вашей БД

---

## 💡 СОВЕТЫ ДЛЯ ЭКЗАМЕНА

1. **Сделайте Find & Replace** перед показом:
   - `creator` → `waiter` (для кафе)
   - `worker` → `cook` (для кафе)
   - `Order` → `Ticket` (для автосервиса)

2. **Подготовьте тестовые данные** заранее:
   - 2-3 пользователя разных ролей
   - 5-10 заказов с разными статусами
   - Позиции в заказах

3. **Продемонстрируйте**:
   - Вход под разными ролями
   - Создание заказа с позициями
   - Изменение статуса заказа
   - Импорт из JSON/Excel

4. **Для быстрой демонстрации** используйте готовых пользователей:
   - admin / admin123
   - creator / creator123
   - worker / worker123

---

## ❗ ВОЗМОЖНЫЕ ПРОБЛЕМЫ И РЕШЕНИЯ

### Ошибка подключения к БД
```
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server...")
```
**Решение:** Проверьте, что MariaDB/MySQL запущен и пользователь имеет доступ.

### Таблицы не создаются
**Решение:** Убедитесь, что база данных `demo_db` существует и у пользователя есть права.

### Ошибка импорта Excel
```
ImportError: openpyxl не установлен
```
**Решение:** `pip install openpyxl`

---

## 📞 КОНТАКТЫ ДЛЯ ПРОВЕРКИ

Готовый шаблон адаптируется под любую тему заменой 3-4 переменных в начале `app.py` и `models.py`.

**Удачи на экзамене! 🍀**
