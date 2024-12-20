### SubscriptionService
Задача: реализовать систему получения и оплаты подписок для онлайн-кинотеатра. 
История задачи: Мы с вами живем в мире подписок: на Yandex музыку, на Кинопоиск, на VK музыку и на многое-многое другое. Мы оплачиваем разными средствами и иногда деньги сами списываются с карточки и это порой удобно. Так подумали в сервисе “Фильмы 8 института” и решили прикрутить к себе подписочный сервис. Ваша задача помочь им в этих стремлениях.

## Запуск
Необходимо:

1. Создать .env файл на основе .env.example
```
cp .env.example .env
```
И исправить YOOKASSA_ACCOUNT_ID и YOOKASSA_SECRET_KEY на свои данные

2. Генерация тестовых сертификатов
```
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
-keyout ./cert/sub_service.key -out ./cert/sub_service.crt
```

3. Прописать
```
docker compose up --build -d
docker exec -it sub_service python3 manage.py migrate
docker exec -it sub_service python3 manage.py collectstatic
```
4. После этого перезапустить
```
docker compose up --build -d
```

## Сваггер
Адрес:
```
http://localhost:8000/api/swagger/
```