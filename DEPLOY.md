# Деплой на сервер (прод)

Прод-стек: `docker-compose.prod.yml` — nginx отдаёт собранный фронт на `:80` и
проксирует API на `/api`, бэкенд на uvicorn без reload, миграции применяются
на старте. Пока нет домена — деплой по IP, поверх HTTP.

> ⚠️ **До деплоя смените root-пароль сервера** (он засветился). Лучше сразу
> перейдите на вход по SSH-ключу и отключите парольный (`PermitRootLogin
> prohibit-password` в `/etc/ssh/sshd_config`, затем `systemctl restart ssh`).

## 1. Docker на сервере (Ubuntu/Debian)

```sh
curl -fsSL https://get.docker.com | sh
docker --version && docker compose version
```

## 2. Код на сервер

```sh
# приватный репозиторий — авторизуйтесь токеном/ключом
git clone https://github.com/redlyaguha/cars-zeekr.git /opt/cars
cd /opt/cars
git checkout prod        # после мержа релиза в prod
```

## 3. Заполнить .env

```sh
cp .env.prod.example .env
# сгенерировать JWT-секрет:
openssl rand -hex 32
nano .env    # подставить все значения с пометкой TODO
```

Обязательно замените: `POSTGRES_PASSWORD` (и тот же пароль в `DATABASE_URL`),
`S3_ACCESS_KEY`/`S3_SECRET_KEY`, `JWT_SECRET`, `ADMIN_PASSWORD`.
`S3_PUBLIC_ENDPOINT` и `CORS_ORIGINS` уже настроены на IP `62.113.44.135` —
поправьте, если IP другой.

## 4. Запуск

```sh
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f api   # дождаться миграций и старта
```

## 5. Демо-данные (по желанию, на пустой базе)

```sh
docker compose -f docker-compose.prod.yml exec api python -m app.seed
```

## 6. Проверка

```sh
curl -i http://62.113.44.135/api/health      # ожидаем 200
```
Открыть `http://62.113.44.135` — сайт. Админка — `http://62.113.44.135/admin`.

## 7. Файрвол

Открыть 22 (SSH), 80 (сайт), 9000 (картинки MinIO). Порты БД/Redis наружу не
публикуются.

```sh
ufw allow 22 && ufw allow 80 && ufw allow 9000 && ufw enable
```

## 8. Обновление версии

```sh
cd /opt/cars && git pull
docker compose -f docker-compose.prod.yml up -d --build
```

## Что доделать после подключения домена

- Прописать домены в `CORS_ORIGINS` и в `S3_PUBLIC_ENDPOINT` (или отдать
  картинки через nginx).
- Поднять TLS (Let's Encrypt / certbot) и увести весь трафик на HTTPS —
  сейчас пароли и токены идут по HTTP.
- Бренд начнёт определяться по hostname автоматически (`perfect-cars.online`
  = РФ, `auto-america.online` = не РФ); `VITE_BRAND` в сборке можно убрать.
