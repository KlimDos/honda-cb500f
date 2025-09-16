# Honda CB500F/CB500X Monitor

Автоматический мониторинг объявлений Honda CB500F и CB500X на Facebook Marketplace с уведомлениями в Telegram.

## Описание

Этот проект отслеживает новые объявления мотоциклов Honda CB500F и CB500X в регионах NY/NJ/PA и отправляет уведомления в Telegram о:
- 🆕 Новых объявлениях
- 💰 Изменениях цен
- 🗑️ Удаленных объявлениях

## Структура проекта

```
cb500f/
├── src/                    # Исходный код мониторинга
│   ├── monitor.py         # Основная логика мониторинга
│   ├── fb_scraper.py      # Скрапер Facebook Marketplace  
│   ├── telegram_notifier.py # Telegram уведомления
│   └── data_storage.py    # Управление данными
├── data/                  # Данные и состояние
│   ├── cookies.json       # Cookies для Facebook
│   └── current_state.json # Текущее состояние объявлений
├── k8s/                   # Kubernetes манифесты
├── old/                   # Старые файлы проекта
├── Dockerfile            # Docker образ
├── requirements.txt      # Python зависимости
└── *.py                  # Скрипты тестирования и запуска
```

## Быстрый старт

### 1. Локальное тестирование

```bash
# Создайте .env файл с токенами
cp .env.example .env
# Отредактируйте .env с вашими токенами

# Тест компонентов
python test_local.py

# Реальный тест с Telegram
python test_real.py

# Полный мониторинг
python run_monitor.py
```

### 2. Docker

```bash
# Сборка образа
docker build -t cb500-monitor:latest .

# Запуск с переменными окружения
docker run --rm \
  -v $(pwd)/data:/app/data \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e TELEGRAM_CHAT_ID=your_chat_id \
  cb500-monitor:latest
```

### 3. Kubernetes

Проект использует External Secrets с Doppler для управления секретами:

```bash
# Убедитесь что External Secrets Operator установлен и настроен Doppler ClusterSecretStore

# Добавьте в Doppler секреты:
# TGTOKEN - токен Telegram бота  
# TELEGRAM_CHAT_ID - ID чата для уведомлений

# Деплой
kubectl apply -k k8s/
```

## Требования

- Python 3.11+
- Docker (для контейнеризации)
- Kubernetes (для продакшн деплоя)
- Telegram Bot Token
- Facebook cookies

## Конфигурация

### Переменные окружения (.env файл):

```bash
# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather
TELEGRAM_CHAT_ID=your_telegram_user_id

# Docker (опционально)
DOCKER_USERNAME=your_docker_hub_username

# Пути (используются по умолчанию)
DATA_DIR=./data
COOKIES_PATH=./data/cookies.json
LOG_LEVEL=INFO
```

### Facebook Cookies

1. Войдите в Facebook в браузере
2. Экспортируйте cookies (используйте расширение "Cookie Editor")
3. Сохраните как `data/cookies.json`

Формат cookies.json:
```json
[
  {
    "name": "c_user", 
    "value": "your_user_id",
    "domain": ".facebook.com",
    "path": "/"
  }
]
```

## Мониторинг

Система проверяет:
- 🔍 **Регионы**: New York Metro, North Jersey, Central Jersey
- 🏍️ **Модели**: CB500F, CB500X, "CB 500F", "CB 500X"  
- 💰 **Цены**: $3,500 - $5,800
- ⏰ **Интервал**: Каждый час (настраивается в k8s/deployment.yaml)

## Статус

Проект готов к использованию в Docker и Kubernetes. Все компоненты протестированы:
- ✅ Скрапинг Facebook Marketplace
- ✅ Telegram уведомления
- ✅ Persistent storage состояния
- ✅ Docker контейнеризация  
- ✅ Kubernetes манифесты

## Логи

Логи мониторинга включают:
- Статистику скрапинга по регионам
- Информацию о новых/измененных объявлениях
- Ошибки отправки в Telegram
- Состояние persistent storage

---

*Старые файлы проекта (анализ данных, веб-интерфейс) перенесены в папку `old/`*

### Сборка образа
```bash
docker build -t your_username/cb500-monitor:latest .
docker push your_username/cb500-monitor:latest
```

### Kubernetes деплой
```bash
# Создайте namespace
kubectl create namespace cb500f

# Обновите secret с вашим токеном
echo -n "your_bot_token" | base64
# Вставьте результат в k8s/secret.yaml

# Примените манифесты
kubectl apply -k k8s/
```

## Мониторинг и отладка

### Посмотреть статус
```bash
kubectl get cronjob -n cb500f
kubectl get jobs -n cb500f
kubectl get pods -n cb500f
```

### Логи
```bash
# Логи последнего запуска
kubectl logs -n cb500f -l app=cb500-monitor

# Логи конкретного pod
kubectl logs -n cb500f <pod-name>
```

### Ручной запуск
```bash
# Запустить задачу вручную для тестирования
kubectl create job -n cb500f --from=cronjob/cb500-monitor manual-test
```

### Локальное тестирование
```bash
# Запуск в Docker локально
docker run -v $(pwd)/cookies.json:/app/data/cookies.json \
  -e TELEGRAM_BOT_TOKEN="your_token" \
  -e TELEGRAM_CHAT_ID="242426387" \
  your_username/cb500-monitor:latest
```

## Настройка

### Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `TELEGRAM_BOT_TOKEN` | Токен Telegram бота | - (обязательно) |
| `TELEGRAM_CHAT_ID` | ID чата для уведомлений | "242426387" |
| `DATA_DIR` | Директория для данных | "/app/data" |
| `COOKIES_PATH` | Путь к файлу cookies | "/app/data/cookies.json" |

### Изменение расписания

Отредактируйте `k8s/cronjob.yaml`:
```yaml
spec:
  # Каждые 30 минут
  schedule: "*/30 * * * *"
  
  # Каждые 2 часа
  schedule: "0 */2 * * *"
  
  # Только в рабочие часы (9-17)
  schedule: "0 9-17 * * *"
```

### Изменение регионов поиска

Отредактируйте `src/monitor.py`, секцию `SEARCH_REGIONS`:
```python
SEARCH_REGIONS = [
    SearchRegion("New York Metro", "103727996333163"),
    SearchRegion("Philadelphia", "112724858717904"),
    # Добавьте свои регионы
]
```

## Структура данных

### Хранение в PersistentVolume
```
/app/data/
├── current_state.json      # Текущее состояние всех объявлений
├── cookies.json           # Facebook cookies
├── historical/            # Исторические данные
│   ├── listings_20250916_100000.json
│   ├── listings_20250916_110000.json
│   └── ...
└── backup_20250916_120000.json  # Автоматические бэкапы
```

### Формат уведомлений

**Новое объявление:**
```
🆕 Новое объявление

🏍 2019 Honda CB500F - $4,200
📍 Newark, NJ
📅 2 days ago
📝 Low miles, excellent condition...

🔗 Смотреть на Facebook
```

**Изменение цены:**
```
📉 Изменение цены

🏍 2020 Honda CB500X - $4,800
📍 Brooklyn, NY

💰 $5,200 → $4,800
📊 Цена снижена на $400

🔗 Смотреть на Facebook
```

## Устранение проблем

### Проблемы с cookies
- Убедитесь, что вы вошли в Facebook
- Обновите cookies если получаете ошибки авторизации
- Cookies могут протухать через несколько недель

### Ошибки скрапинга
- Facebook может изменить структуру страниц
- Проверьте логи на ошибки селекторов
- Возможна временная блокировка при частых запросах

### Telegram не работает
- Проверьте токен бота
- Убедитесь, что бот может писать в указанный чат
- Отправьте `/start` боту для активации

### Kubernetes проблемы
```bash
# Проверить состояние ресурсов
kubectl get all -n cb500f

# Проверить события
kubectl get events -n cb500f

# Описание pod для деталей
kubectl describe pod -n cb500f <pod-name>
```

## Безопасность

- Никогда не коммитьте `cookies.json` в git
- Используйте Kubernetes secrets для токенов
- Регулярно обновляйте cookies
- Мониторьте логи на подозрительную активность

## Обновление

```bash
# Пересобрать и загрузить новую версию
docker build -t your_username/cb500-monitor:v1.1 .
docker push your_username/cb500-monitor:v1.1

# Обновить в Kubernetes
kubectl set image cronjob/cb500-monitor -n cb500f monitor=your_username/cb500-monitor:v1.1
```

## Лицензия

Проект предназначен только для личного использования. Соблюдайте Terms of Service Facebook при использовании.
