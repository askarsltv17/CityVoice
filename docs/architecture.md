# Архитектура CityVoice

## 1. Слои системы

- `Frontend` - шаблоны `templates/`, стили `static/styles.css`, клиентская логика `static/script.js`.
- `Backend` - `Flask`-приложение в `app.py`, API, авторизация, публикации, модерация, уведомления.
- `Database` - `PostgreSQL` как основное runtime-хранилище, описание схемы и подключение в `db.py`.

## 2. Основные модули

### Пользователи

- регистрация и вход;
- хранение ролей `user`, `moderator`, `admin`;
- профиль пользователя;
- восстановление пароля по email.

### Жалобы

- создание, редактирование и удаление жалоб;
- отображение в общей ленте;
- фильтрация и сортировка на клиенте;
- изменение статуса администратором.

### Петиции

- создание, редактирование и удаление петиций;
- голосование с защитой от повторного голоса;
- комментарии и реакции;
- изменение статуса администратором.

### Модерация

- жалобы на контент;
- просмотр репортов модератором;
- удаление публикаций по репортам;
- просмотр пользователей администратором и смена роли.

### Уведомления

- уведомления о голосах за петиции;
- уведомления об изменении статуса жалоб и петиций;
- отметка уведомлений как прочитанных.

## 3. Реализованный стек

- `Frontend`: `HTML`, `CSS`, `JavaScript`
- `Backend`: `Python 3.13`, `Flask`
- `Database`: `PostgreSQL`
- `Auth`: серверные сессии, хеширование паролей через `Werkzeug`
- `Mail`: `Flask-Mail`

## 4. Основные API-маршруты

### Аутентификация и профиль

- `POST /api/register`
- `POST /api/login`
- `POST /api/logout`
- `GET /api/me`
- `PATCH /api/profile`
- `POST /api/password-reset/request`
- `POST /api/password-reset/confirm/<token>`

### Жалобы

- `GET /api/complaints`
- `POST /api/complaints`
- `PATCH /api/complaints/<complaint_id>`
- `DELETE /api/complaints/<complaint_id>`

### Петиции

- `GET /api/petitions`
- `POST /api/petitions`
- `PATCH /api/petitions/<petition_id>`
- `DELETE /api/petitions/<petition_id>`
- `POST /api/petitions/<petition_id>/vote`

### Комментарии, реакции и репорты

- `GET /api/<kind>/<content_id>/comments`
- `POST /api/<kind>/<content_id>/comments`
- `DELETE /api/comments/<comment_id>`
- `POST /api/<kind>/<content_id>/reactions`
- `POST /api/<kind>/<content_id>/report`

### Модерация и администрирование

- `GET /api/moderation/reports`
- `POST /api/moderation/reports/<report_id>/approve`
- `POST /api/moderation/reports/<report_id>/delete-post`
- `PATCH /api/admin/complaints/<complaint_id>/status`
- `PATCH /api/admin/petitions/<petition_id>/status`
- `GET /api/admin/users`
- `PATCH /api/admin/users/<user_id>/role`
