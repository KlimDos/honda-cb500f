# Makefile для быстрой разработки CB500F мониторинга

.PHONY: help build-base build-fast build-microsoft build-normal deploy test clean status logs

# Переменные
REGISTRY = klimdos
APP_NAME = cb500-monitor
BASE_NAME = cb500-base
NAMESPACE = cb500f

# Цвета для вывода
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
RED = \033[0;31m
NC = \033[0m # No Color

help: ## Показать справку
	@echo "$(BLUE)CB500F Docker Build & Deploy Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "$(GREEN)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build-base: ## Создать базовый образ (один раз)
	@echo "$(YELLOW)🔨 Создание базового образа...$(NC)"
	./fast-build.sh build-base
	@echo "$(GREEN)✅ Базовый образ создан$(NC)"

push-base: ## Опубликовать базовый образ
	@echo "$(BLUE)📤 Публикация базового образа...$(NC)"
	./fast-build.sh push-base
	@echo "$(GREEN)✅ Базовый образ опубликован$(NC)"

build-fast: ## Быстрая сборка приложения
	@echo "$(GREEN)🚀 Быстрая сборка приложения...$(NC)"
	./fast-build.sh build-fast
	@echo "$(GREEN)✅ Приложение собрано$(NC)"

build-microsoft: ## Сборка с Microsoft Playwright базой
	@echo "$(BLUE)🐧 Сборка с Microsoft базой...$(NC)"
	./fast-build.sh build-microsoft

build-normal: ## Обычная сборка (медленно)
	@echo "$(RED)🐌 Обычная сборка...$(NC)"
	./fast-build.sh build-normal

test: ## Сравнить время сборки всех методов
	@echo "$(YELLOW)⏱️ Тестирование производительности...$(NC)"
	./fast-build.sh time-test

deploy: ## Деплой в Kubernetes
	@echo "$(BLUE)🚀 Деплой в Kubernetes...$(NC)"
	kubectl set image cronjob/cb500-monitor monitor=$(REGISTRY)/$(APP_NAME):latest -n $(NAMESPACE)
	@echo "$(GREEN)✅ Образ обновлен в Kubernetes$(NC)"

deploy-config: ## Применить все манифесты Kubernetes
	@echo "$(BLUE)⚙️ Применение конфигурации Kubernetes...$(NC)"
	kubectl apply -f k8s/
	@echo "$(GREEN)✅ Конфигурация применена$(NC)"

status: ## Проверить статус в Kubernetes
	@echo "$(BLUE)📊 Статус в Kubernetes:$(NC)"
	@echo ""
	@echo "$(YELLOW)Pods:$(NC)"
	kubectl get pods -n $(NAMESPACE)
	@echo ""
	@echo "$(YELLOW)CronJobs:$(NC)"
	kubectl get cronjobs -n $(NAMESPACE)
	@echo ""
	@echo "$(YELLOW)Recent Jobs:$(NC)"
	kubectl get jobs -n $(NAMESPACE) --sort-by=.metadata.creationTimestamp | tail -5

logs: ## Посмотреть логи последней задачи
	@echo "$(BLUE)📝 Логи последней задачи:$(NC)"
	@POD=$$(kubectl get pods -n $(NAMESPACE) -l job-name --sort-by=.metadata.creationTimestamp -o jsonpath='{.items[-1].metadata.name}' 2>/dev/null); \
	if [ -n "$$POD" ]; then \
		kubectl logs $$POD -n $(NAMESPACE); \
	else \
		echo "$(RED)❌ Не найдено выполненных задач$(NC)"; \
	fi

test-run: ## Запустить тестовую задачу
	@echo "$(YELLOW)🧪 Запуск тестовой задачи...$(NC)"
	kubectl create job test-monitor-$$(date +%s) --from=cronjob/cb500-monitor -n $(NAMESPACE)
	@echo "$(GREEN)✅ Тестовая задача создана$(NC)"

debug-db: ## Посмотреть содержимое базы данных
	@echo "$(BLUE)🔍 Содержимое базы данных:$(NC)"
	@POD=$$(kubectl get pods -n $(NAMESPACE) -l app=cb500-monitor --field-selector=status.phase=Running -o jsonpath='{.items[0].metadata.name}' 2>/dev/null); \
	if [ -n "$$POD" ]; then \
		kubectl exec $$POD -n $(NAMESPACE) -- python /app/view_database.py /app/data/current_state.json; \
	else \
		echo "$(RED)❌ Нет запущенных подов$(NC)"; \
	fi

verbose-on: ## Включить детальное логирование
	@echo "$(YELLOW)🔍 Включение verbose логирования...$(NC)"
	kubectl patch configmap cb500-monitor-config -n $(NAMESPACE) --patch '{"data":{"VERBOSE_LOGGING":"true"}}'
	@echo "$(GREEN)✅ Verbose логирование включено$(NC)"

verbose-off: ## Выключить детальное логирование
	@echo "$(BLUE)🔇 Выключение verbose логирования...$(NC)"
	kubectl patch configmap cb500-monitor-config -n $(NAMESPACE) --patch '{"data":{"VERBOSE_LOGGING":"false"}}'
	@echo "$(GREEN)✅ Verbose логирование выключено$(NC)"

days-7: ## Установить поиск за 7 дней
	@echo "$(YELLOW)📅 Установка поиска за 7 дней...$(NC)"
	kubectl patch configmap cb500-monitor-config -n $(NAMESPACE) --patch '{"data":{"DAYS_SINCE_LISTED":"7"}}'
	@echo "$(GREEN)✅ Установлен поиск за 7 дней$(NC)"

days-14: ## Установить поиск за 14 дней
	@echo "$(YELLOW)📅 Установка поиска за 14 дней...$(NC)"
	kubectl patch configmap cb500-monitor-config -n $(NAMESPACE) --patch '{"data":{"DAYS_SINCE_LISTED":"14"}}'
	@echo "$(GREEN)✅ Установлен поиск за 14 дней$(NC)"

days-30: ## Установить поиск за 30 дней
	@echo "$(YELLOW)📅 Установка поиска за 30 дней...$(NC)"
	kubectl patch configmap cb500-monitor-config -n $(NAMESPACE) --patch '{"data":{"DAYS_SINCE_LISTED":"30"}}'
	@echo "$(GREEN)✅ Установлен поиск за 30 дней$(NC)"

clean: ## Очистить неиспользуемые Docker образы
	@echo "$(YELLOW)🧹 Очистка Docker...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✅ Очистка завершена$(NC)"

setup: ## Первоначальная настройка (создать базу + собрать приложение)
	@echo "$(BLUE)🚀 Первоначальная настройка...$(NC)"
	$(MAKE) build-base
	$(MAKE) push-base
	$(MAKE) build-fast
	$(MAKE) deploy-config
	@echo "$(GREEN)✅ Настройка завершена!$(NC)"

dev: ## Режим разработки (быстрая сборка + деплой)
	@echo "$(GREEN)👨‍💻 Режим разработки...$(NC)"
	$(MAKE) build-fast
	$(MAKE) deploy
	@echo "$(GREEN)✅ Готово к тестированию!$(NC)"

info: ## Показать информацию о проекте
	@echo "$(BLUE)📊 Информация о проекте CB500F:$(NC)"
	@echo ""
	@echo "$(YELLOW)Docker образы:$(NC)"
	@docker images | grep -E "($(REGISTRY)/$(APP_NAME)|$(REGISTRY)/$(BASE_NAME))" || echo "Нет локальных образов"
	@echo ""
	@echo "$(YELLOW)Kubernetes ресурсы:$(NC)"
	@kubectl get all -n $(NAMESPACE) 2>/dev/null || echo "Namespace не найден"
	@echo ""
	@echo "$(YELLOW)Полезные команды:$(NC)"
	@echo "  make dev           - Быстрая разработка"
	@echo "  make test-run      - Запустить тест"
	@echo "  make logs          - Посмотреть логи"
	@echo "  make debug-db      - Посмотреть базу"
