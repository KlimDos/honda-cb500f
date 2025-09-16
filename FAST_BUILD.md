# 🚀 Быстрая сборка Docker образов CB500F

## Проблема:
Обычная сборка занимает **6 минут** из-за установки системных зависимостей и Playwright браузеров.

## Решения:

### 🎯 СТРАТЕГИЯ 1: Базовый образ (РЕКОМЕНДУЕТСЯ)
**Время сборки: 10-20 секунд после создания базы**

```bash
# 1. Создать базовый образ (один раз, 5-6 минут)
./fast-build.sh build-base

# 2. Быстрая сборка приложения (10-20 секунд)
./fast-build.sh build-fast

# 3. Опубликовать базовый образ (один раз)
./fast-build.sh push-base
```

### 🐧 СТРАТЕГИЯ 2: Microsoft Playwright образ
**Время сборки: 1-2 минуты**

```bash
# Использует готовый mcr.microsoft.com/playwright образ
./fast-build.sh build-microsoft
```

### 🔍 Сравнение всех методов:
```bash
./fast-build.sh time-test
```

## Файлы для разных стратегий:

1. **Dockerfile.base** - Создание базового образа
2. **Dockerfile.superfast** - Супер-быстрая сборка с базой
3. **Dockerfile.fast** - Быстрая сборка с Microsoft
4. **Dockerfile** - Оригинальный (медленный)

## Настройка CI/CD:

### GitHub Actions с кэшированием:
```yaml
# .github/workflows/docker.yml
name: Fast Docker Build

on:
  push:
    branches: [ main ]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4
    
    - name: Cache Docker layers
      uses: actions/cache@v3
      with:
        path: /tmp/.buildx-cache
        key: ${{ runner.os }}-buildx-${{ github.sha }}
        restore-keys: |
          ${{ runner.os }}-buildx-
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3
    
    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}
    
    - name: Build and push
      uses: docker/build-push-action@v5
      with:
        context: .
        file: ./Dockerfile.fast
        push: true
        tags: klimdos/cb500-monitor:latest
        cache-from: type=local,src=/tmp/.buildx-cache
        cache-to: type=local,dest=/tmp/.buildx-cache-new,mode=max
```

### Kubernetes с быстрым образом:
```yaml
# k8s/cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: cb500-monitor
  namespace: cb500f
spec:
  schedule: "0 */4 * * *"  # Каждые 4 часа
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: monitor
            image: klimdos/cb500-monitor:latest  # Быстро собранный образ
            # ... остальная конфигурация
```

## Команды для разработки:

### Первоначальная настройка:
```bash
# 1. Создать и опубликовать базовый образ (один раз)
./fast-build.sh build-base
./fast-build.sh push-base

# 2. Настроить Git hook для автобилда
echo './fast-build.sh build-fast' > .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### Ежедневная разработка:
```bash
# Быстрая сборка при изменениях кода
./fast-build.sh build-fast

# Деплой в Kubernetes
kubectl set image cronjob/cb500-monitor monitor=klimdos/cb500-monitor:latest -n cb500f
```

### Обновление зависимостей:
```bash
# При изменении requirements.txt
./fast-build.sh build-base  # Пересоздать базу
./fast-build.sh push-base   # Опубликовать
./fast-build.sh build-fast  # Собрать приложение
```

## Размеры образов:

| Стратегия | Время сборки | Размер образа | Кэшируемость |
|-----------|--------------|---------------|--------------|
| Оригинальный | 6 минут | ~800MB | Плохая |
| Microsoft base | 1-2 минуты | ~1.2GB | Хорошая |
| Собственный base | 10-20 секунд | ~800MB | Отличная |

## Автоматизация:

### Makefile для удобства:
```makefile
# Makefile
.PHONY: build-base build-fast deploy test

build-base:
	./fast-build.sh build-base
	./fast-build.sh push-base

build-fast:
	./fast-build.sh build-fast

deploy:
	kubectl set image cronjob/cb500-monitor monitor=klimdos/cb500-monitor:latest -n cb500f

test:
	./fast-build.sh time-test

all: build-fast deploy
```

Использование:
```bash
make build-base  # Первый раз
make build-fast  # Быстрая сборка
make deploy      # Деплой
make test        # Тестирование
```

## Результат:
- **Время разработки**: С 6 минут до 10-20 секунд
- **CI/CD**: В 3-6 раз быстрее
- **Размер**: Без увеличения
- **Кэширование**: Отличное
