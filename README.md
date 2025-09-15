# Honda CB500F Used Market Toolkit (NJ, NY, PA, MD, VA)

Русскоязычный набор инструментов для оценки выгодности покупки Honda CB500F на вторичном рынке северо-востока США.

## Содержимое
* `data/price_reference_cb500f.csv` — базовая таблица ориентиров цен по годам.
* `analysis/methodology_cb500f.md` — методология модели и формулы.
* `cb500f_calculator.py` — CLI калькулятор справедливой цены и классификации сделки.
* `app/` — FastAPI приложение (веб-форма + страницы методологии и стратегии).
* `templates/`, `static/` — шаблоны и стили фронтенда.
* `Dockerfile`, `requirements.txt` — контейнеризация и зависимости.
* `guides/fb_marketplace_strategy.md` — практическое руководство по поиску и торгу на FB Marketplace.

## Быстрый старт
```
python3 cb500f_calculator.py --year 2019 --mileage 14000 --price 4700 --region NJ --condition good --abs --crashbars --new_tires
```

Если не указывать параметры — скрипт перейдёт в интерактивный режим.

## Интерпретация
* Great Deal — заметно ниже модели (<=90% fair или большое абсолютное отклонение)
* Good Deal — 90–97% fair
* Fair — 97–107% fair
* Overpriced — >107% fair

Рекомендуемый коридор предложения: 88–94% от fair (скорректировать по состоянию расходников).

## Обновление таблицы
См. раздел в методологии. При сдвиге медианы на >$250 или >5% по году — обновить `base_mid_usd`.

## Дисклеймер
Все цифры — ориентиры. Перед сделкой сверяйте с реальными активными объявлениями. Модель не заменяет профессиональный осмотр.

Обновлено: 2025-09-14.

## Веб-приложение (FastAPI)

### Локальный запуск
```
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Откройте: http://127.0.0.1:8000

Страницы:
* `/` — форма ввода параметров объявления.
* `/methodology` — текст методологии (raw markdown).
* `/strategy` — гайд по FB Marketplace.

### Docker
```
docker build -t cb500f-toolkit .
docker run --rm -p 8000:8000 cb500f-toolkit
```
Откройте: http://localhost:8000

### Переменные окружения
На текущий момент не требуются. Можно добавить (TODO): управление годом `CURRENT_YEAR`, включение сезонного коэффициента.

### Тестовый запрос (CLI)
После запуска контейнера/локально:
```
curl -X POST -F year=2019 -F mileage=14000 -F price=4700 -F region=NJ -F condition=good http://localhost:8000/
```
Вы получите HTML (форма + результат). Для JSON эндпоинта можно добавить отдельный `/api/evaluate` (TODO расширение).

## CI/CD: GitHub Actions Docker Publish

Репозиторий содержит workflow `.github/workflows/docker-publish.yml` который:
* Триггеры: push в `main`, теги вида `v*.*.*`, pull request, ручной запуск.
* Строит multi-arch образ (linux/amd64, linux/arm64) с Docker Buildx.
* Генерирует теги: `latest` (для default branch), имя ветки, семантический тег, SHA.
* Пушит в Docker Hub.

### Требуемые секреты GitHub
В настройках репозитория `Settings -> Secrets and variables -> Actions` создайте:
* `DOCKERHUB_USERNAME` — ваш логин Docker Hub
* `DOCKERHUB_TOKEN` — токен/пароль access token с правами push

### Локальная проверка перед пушем тега
```
docker build -t cb500f-toolkit:dev .
docker run --rm -p 8000:8000 cb500f-toolkit:dev
```

### Публикация релиза
```
git tag -a v0.1.0 -m "First release"
git push origin v0.1.0
```
Workflow создаст соответствующие теги образа.


## Возможные улучшения фронтенда (идея)
* Рендер markdown в HTML (mistune / markdown2) вместо `<pre>`.
* Client-side сохранение последнего ввода (localStorage).
* Endpoint `/api/evaluate` с JSON.
* Модуль сезонной коррекции по месяцу автоматически.

