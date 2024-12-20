### SubscriptionService
## Запуск
Необходимо:

1. Создать .env файл на основе .env.example
```
cp .env.example .env
```
И исправить YOOKASSA_ACCOUNT_ID и YOOKASSA_SECRET_KEY на свои данные

2. Прописать
```
docker compose up --build -d
docker exec -it sub_service python3 manage.py migrate
docker exec -it sub_service python3 manage.py collectstatic
```
2. После этого перезапустить
```
docker compose up --build -d
```

## Сваггер
Адрес:
```
http://localhost:8000/api/swagger/
```

## Генерация тестовых сертификатов
```
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
-keyout ./cert/sub_service.key -out ./cert/sub_service.crt
```