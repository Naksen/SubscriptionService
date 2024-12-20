### SubscriptionService
## Запуск
Прописать
```
docker compose up --build -d
docker exec -it sub_service python3 manage.py migrate
docker exec -it sub_service python3 manage.py collectstatic
```
После этого перезапустить
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
-keyout sub_service.key -out sub_service.crt
```