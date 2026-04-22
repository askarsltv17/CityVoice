# Схема базы данных CityVoice

## Runtime-хранилище

Основная база проекта - `PostgreSQL`.

Подключение настраивается через `.env`:

- `CITYVOICE_DATABASE_URL`
- или набор переменных `CITYVOICE_POSTGRES_HOST`, `CITYVOICE_POSTGRES_PORT`, `CITYVOICE_POSTGRES_DB`, `CITYVOICE_POSTGRES_USER`, `CITYVOICE_POSTGRES_PASSWORD`

Файл `instance/cityvoice.db` рассматривается только как legacy-источник для миграции старых данных.

## Таблицы

### users

- `id` - уникальный идентификатор пользователя
- `name` - отображаемое имя
- `email` - уникальная почта
- `password_hash` - хеш пароля
- `role` - `user`, `moderator`, `admin`
- `last_name`
- `first_name`
- `middle_name`
- `birth_year`
- `avatar_data`
- `created_at`

### complaints

- `id`
- `title`
- `category`
- `district`
- `description`
- `status`
- `author_id` - ссылка на `users.id`
- `latitude`
- `longitude`
- `created_at`
- `updated_at`

### petitions

- `id`
- `title`
- `category`
- `district`
- `description`
- `goal`
- `votes`
- `status`
- `author_id` - ссылка на `users.id`
- `created_at`
- `updated_at`

### petition_votes

- `id`
- `petition_id` - ссылка на `petitions.id`
- `user_id` - ссылка на `users.id`
- `created_at`
- уникальная пара `petition_id + user_id`

### comments

- `id`
- `content_type` - `complaint` или `petition`
- `content_id`
- `user_id` - ссылка на `users.id`
- `body`
- `created_at`
- `updated_at`

### reactions

- `id`
- `content_type`
- `content_id`
- `user_id` - ссылка на `users.id`
- `emoji`
- `created_at`
- уникальная тройка `content_type + content_id + user_id`

### moderation_reports

- `id`
- `content_type`
- `content_id`
- `reporter_id` - ссылка на `users.id`
- `reason`
- `status`
- `created_at`

### notifications

- `id`
- `user_id` - ссылка на `users.id`
- `type`
- `message`
- `link`
- `is_read`
- `created_at`

### password_resets

- `id`
- `user_id` - ссылка на `users.id`
- `token`
- `expires_at`
- `used`
- `created_at`

## Связи

- один пользователь может создать много жалоб;
- один пользователь может создать много петиций;
- один пользователь может оставить много комментариев;
- одна петиция может иметь много голосов;
- один пользователь может проголосовать за конкретную петицию только один раз;
- один пользователь может получить много уведомлений;
- один пользователь может отправить много жалоб на контент.
