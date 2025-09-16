#!/bin/bash

# Скрипт для управления быстрой сборкой Docker образов
# СТРАТЕГИИ УСКОРЕНИЯ БИЛДА

set -e

REGISTRY="klimdos"
APP_NAME="cb500-monitor"
BASE_NAME="cb500-base"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_help() {
    echo -e "${BLUE}Скрипт для быстрой сборки CB500 мониторинга${NC}"
    echo ""
    echo "КОМАНДЫ:"
    echo "  build-base      - Создать базовый образ (один раз)"
    echo "  build-fast      - Быстрая сборка приложения"
    echo "  build-microsoft - Сборка на базе Microsoft Playwright"
    echo "  build-normal    - Обычная сборка (медленно)"
    echo "  push-base       - Запушить базовый образ"
    echo "  push-app        - Запушить образ приложения"
    echo "  time-test       - Сравнить время сборки"
    echo ""
    echo "ПРИМЕРЫ:"
    echo "  ./fast-build.sh build-base      # Один раз создать базу"
    echo "  ./fast-build.sh build-fast      # Быстрая сборка"
    echo "  ./fast-build.sh time-test       # Сравнить скорости"
}

build_base() {
    echo -e "${YELLOW}🔨 Создание базового образа (делается один раз)...${NC}"
    echo "Это займет 5-6 минут, но потом приложение будет собираться за 10-20 секунд"
    
    docker build -f Dockerfile.base -t $REGISTRY/$BASE_NAME:latest .
    
    echo -e "${GREEN}✅ Базовый образ создан: $REGISTRY/$BASE_NAME:latest${NC}"
    echo "Размер образа:"
    docker images $REGISTRY/$BASE_NAME:latest
}

build_fast() {
    echo -e "${GREEN}🚀 Быстрая сборка приложения...${NC}"
    
    # Проверяем наличие базового образа
    if ! docker images $REGISTRY/$BASE_NAME:latest | grep -q $BASE_NAME; then
        echo -e "${RED}❌ Базовый образ не найден!${NC}"
        echo "Сначала выполните: ./fast-build.sh build-base"
        exit 1
    fi
    
    start_time=$(date +%s)
    
    docker build -f Dockerfile.superfast -t $REGISTRY/$APP_NAME:latest .
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo -e "${GREEN}✅ Приложение собрано за $duration секунд!${NC}"
    docker images $REGISTRY/$APP_NAME:latest
}

build_microsoft() {
    echo -e "${BLUE}🐧 Сборка на базе Microsoft Playwright образа...${NC}"
    
    start_time=$(date +%s)
    
    docker build -f Dockerfile.fast -t $REGISTRY/$APP_NAME:microsoft .
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo -e "${GREEN}✅ Сборка завершена за $duration секунд!${NC}"
    docker images $REGISTRY/$APP_NAME:microsoft
}

build_normal() {
    echo -e "${RED}🐌 Обычная сборка (медленно)...${NC}"
    
    start_time=$(date +%s)
    
    docker build -f Dockerfile -t $REGISTRY/$APP_NAME:normal .
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    echo -e "${YELLOW}⏱️ Обычная сборка завершена за $duration секунд${NC}"
    docker images $REGISTRY/$APP_NAME:normal
}

push_base() {
    echo -e "${BLUE}📤 Публикация базового образа...${NC}"
    docker push $REGISTRY/$BASE_NAME:latest
    echo -e "${GREEN}✅ Базовый образ опубликован${NC}"
}

push_app() {
    echo -e "${BLUE}📤 Публикация образа приложения...${NC}"
    docker push $REGISTRY/$APP_NAME:latest
    echo -e "${GREEN}✅ Образ приложения опубликован${NC}"
}

time_test() {
    echo -e "${YELLOW}⏱️ Тестирование времени сборки...${NC}"
    echo ""
    
    # Проверяем базовый образ
    if ! docker images $REGISTRY/$BASE_NAME:latest | grep -q $BASE_NAME; then
        echo -e "${YELLOW}Базовый образ не найден, создаем...${NC}"
        build_base
        echo ""
    fi
    
    echo -e "${GREEN}1. Тест быстрой сборки:${NC}"
    build_fast
    echo ""
    
    echo -e "${BLUE}2. Тест Microsoft Playwright:${NC}"
    build_microsoft
    echo ""
    
    echo -e "${RED}3. Тест обычной сборки:${NC}"
    build_normal
    
    echo ""
    echo -e "${YELLOW}📊 СРАВНЕНИЕ РАЗМЕРОВ:${NC}"
    docker images | grep cb500
}

# Главная логика
case "$1" in
    build-base)
        build_base
        ;;
    build-fast)
        build_fast
        ;;
    build-microsoft)
        build_microsoft
        ;;
    build-normal)
        build_normal
        ;;
    push-base)
        push_base
        ;;
    push-app)
        push_app
        ;;
    time-test)
        time_test
        ;;
    help|--help|-h)
        print_help
        ;;
    *)
        echo -e "${RED}❌ Неизвестная команда: $1${NC}"
        echo ""
        print_help
        exit 1
        ;;
esac
