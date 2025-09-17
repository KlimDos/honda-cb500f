# CB500F Monitor

Автоматический мониторинг Honda CB500F/CB500X на Facebook Marketplace с уведомлениями в Telegram.

## Что делает

- Скрапит объявления Honda CB500F/CB500X на Facebook Marketplace
- Отправляет уведомления в Telegram о новых объявлениях и изменениях цен
- Работает в Kubernetes как CronJob
- Сохраняет состояние в persistent volume

## Быстрый запуск

### 1. Настройка секретов

В Doppler или Kubernetes секретах настройте:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 2. Деплой в Kubernetes

```bash
kubectl apply -f k8s/
```

## Конфигурация

Настройки в `k8s/configmap.yaml`:

```yaml
DAYS_SINCE_LISTED: "14"    # Поиск за N дней
VERBOSE_LOGGING: "false"   # Детальные логи
```

## Мониторинг

```bash
# Статус
kubectl get cronjobs -n cb500f
kubectl get pods -n cb500f

# Логи
kubectl logs -n cb500f -l app=cb500-monitor --tail=50

# Просмотр базы данных
kubectl exec -it <pod-name> -n cb500f -- python /app/view_database.py /app/data/current_state.json --detailed

# Ручной запуск
kubectl create job manual-test --from=cronjob/cb500-monitor -n cb500f
```

## Структура

```
cb500f/
├── src/                    # Исходный код
│   ├── monitor.py         # Основной скрипт
│   ├── fb_scraper.py      # Facebook scraper
│   ├── telegram_notifier.py # Telegram bot
│   └── view_database.py   # Просмотр данных
├── k8s/                   # Kubernetes манифесты
├── Dockerfile            # Docker образ
└── requirements.txt      # Python зависимости
```

Docker образ собирается автоматически в GitHub Actions и публикуется как `klimdos/cb500-monitor:latest`.
