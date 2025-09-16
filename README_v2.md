# Улучшения мониторинга CB500F v2.0

## Сделанные изменения:

### 1. 📅 Настраиваемый временной диапазон
- **Переменная окружения**: `DAYS_SINCE_LISTED` (по умолчанию: 14)
- **Как изменить**: 
  ```bash
  kubectl patch configmap cb500-monitor-config -n cb500f --patch '{"data":{"DAYS_SINCE_LISTED":"30"}}'
  ```
- **Варианты**: 7, 14, 30 дней

### 2. 📊 Одно сообщение саммари вместо спама
- **Раньше**: Отдельное сообщение для каждого нового объявления
- **Сейчас**: Одно сообщение с полной сводкой изменений
- **Формат**:
  ```
  📊 СВОДКА ИЗМЕНЕНИЙ
  
  🆕 Новых объявлений: 2
  
  🏍 2023 Honda CB500F - $5,495
  📍 Dover, DE
  🔗 https://facebook.com/...
  
  ❌ Удаленных объявлений: 1
  💰 Изменений цены: 0
  ```

### 3. ✅ Исправлено форматирование Telegram
- **Убраны HTML теги**: `<b>`, `<a href="">` и другие
- **Простой текст**: Telegram корректно отображает сообщения
- **Emojis**: Используются для визуального разделения

### 4. 🔍 Просмотр базы данных через kubectl

#### Быстрый просмотр текущего состояния:
```bash
# Получить имя активного пода
POD_NAME=$(kubectl get pods -n cb500f -l app=cb500-monitor --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}')

# Краткая сводка
kubectl exec $POD_NAME -n cb500f -- python /app/view_database.py /app/data/current_state.json

# Детальный просмотр
kubectl exec $POD_NAME -n cb500f -- python /app/view_database.py /app/data/current_state.json --detailed
```

#### Просмотр исторических данных:
```bash
# Список всех исторических файлов
kubectl exec $POD_NAME -n cb500f -- ls -la /app/data/historical/

# Просмотр конкретного файла
kubectl exec $POD_NAME -n cb500f -- python /app/view_database.py /app/data/historical/listings_20250916_204506.json

# С деталями
kubectl exec $POD_NAME -n cb500f -- python /app/view_database.py /app/data/historical/listings_20250916_204506.json --detailed
```

#### Быстрые команды через pipe:
```bash
# Текущее состояние в JSON
kubectl exec $POD_NAME -n cb500f -- cat /app/data/current_state.json | python view_database.py - 

# Количество объявлений
kubectl exec $POD_NAME -n cb500f -- cat /app/data/current_state.json | jq length

# Только ID объявлений
kubectl exec $POD_NAME -n cb500f -- cat /app/data/current_state.json | jq -r '.[].listing_id'
```

### 5. 🔧 Улучшенные переменные окружения

Обновленный ConfigMap:
```yaml
data:
  DATA_DIR: "/app/data"
  COOKIES_PATH: "/app/data/cookies.json"
  LOG_LEVEL: "INFO"
  VERBOSE_LOGGING: "false"        # true = детальные логи
  DAYS_SINCE_LISTED: "14"         # 7, 14, 30 дней
```

## Команды для применения изменений:

### Обновить ConfigMap:
```bash
kubectl apply -f k8s/configmap.yaml
```

### Изменить диапазон дней (без перезапуска):
```bash
# 7 дней
kubectl patch configmap cb500-monitor-config -n cb500f --patch '{"data":{"DAYS_SINCE_LISTED":"7"}}'

# 30 дней
kubectl patch configmap cb500-monitor-config -n cb500f --patch '{"data":{"DAYS_SINCE_LISTED":"30"}}'
```

### Включить verbose логирование:
```bash
kubectl patch configmap cb500-monitor-config -n cb500f --patch '{"data":{"VERBOSE_LOGGING":"true"}}'
```

### Создать тестовую задачу:
```bash
kubectl create job test-monitor-$(date +%s) --from=cronjob/cb500-monitor -n cb500f
```

### Проверить логи последней задачи:
```bash
kubectl logs -l job-name --since=1h -n cb500f --tail=100
```

## Пример работы новой системы:

### Логи с улучшенной статистикой:
```
2025-09-16 21:25:06,440 - INFO - Starting monitor cycle
2025-09-16 21:25:44,193 - INFO - Found 2 relevant listings in New York Metro
2025-09-16 21:26:26,584 - INFO - Found 3 relevant listings in Philadelphia
Region New York Metro: 5 total listings found
Region Philadelphia: 8 total listings found
Total unique listings found: 7
Regional breakdown: {'New York Metro': 5, 'Philadelphia': 8, 'Maryland': 2}
Duplicates removed: 8
Found 3 changes
```

### Telegram сообщение:
```
📊 СВОДКА ИЗМЕНЕНИЙ

🆕 Новых объявлений: 2

🏍 2023 Honda CB500F - $5,495
📍 Dover, DE
🔗 https://www.facebook.com/marketplace/item/1984086672351158/

🏍 2022 Honda CB500F - $5,500  
📍 Long Valley, NJ
🔗 https://www.facebook.com/marketplace/item/1469810090903514/

❌ Удаленных объявлений: 1
```

## Следующие возможные улучшения:

1. **Фильтрация по расстоянию**: Добавить радиус в милях
2. **Фильтрация по году**: Только мотоциклы от 2020 года
3. **Webhook уведомления**: Интеграция с Discord/Slack
4. **График цен**: Отслеживание изменений цен во времени
5. **Автоматический дилер-детект**: Исключение дилерских объявлений

## Мониторинг эффективности:

Теперь в логах можно легко увидеть:
- Сколько объявлений найдено в каждом регионе
- Сколько дублей удалено
- Общую статистику поиска
- Четкие и читаемые уведомления в Telegram
