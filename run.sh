#!/bin/bash

################################################################################
# GARAMe Manager - 통합 실행 스크립트
# Ubuntu 25 환경 최적화
################################################################################

set -e  # 오류 발생 시 즉시 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 스크립트 디렉토리로 이동
cd "$(dirname "$0")"

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 배너 출력
print_banner() {
    echo "========================================="
    echo "  GARAMe Manager v2.0.1"
    echo "  실행 스크립트"
    echo "========================================="
    echo ""
}

# 가상환경 확인
check_virtual_env() {
    if [ ! -d "venv" ]; then
        log_error "가상환경이 설치되지 않았습니다."
        log_info "먼저 install.sh를 실행하세요:"
        log_info "  ./install.sh"
        exit 1
    fi
}

# Python 확인
check_python() {
    if ! command -v python3 &> /dev/null; then
        log_error "Python3가 설치되지 않았습니다."
        log_info "먼저 install.sh를 실행하세요:"
        log_info "  ./install.sh"
        exit 1
    fi
}

# 실행 중인 프로세스 확인
check_running_process() {
    # 자동 시작 모드면 대화형 프롬프트 생략
    if [ "${AUTO_MODE:-false}" = "true" ]; then
        if pgrep -f "garame_manager\|python.*main.py" > /dev/null; then
            log_info "GARAMe Manager가 이미 실행 중입니다. 종료합니다."
            exit 0
        fi
        return
    fi

    if pgrep -f "garame_manager\|python.*main.py" > /dev/null; then
        log_warning "GARAMe Manager가 이미 실행 중입니다."
        log_info "기존 프로세스를 종료하시겠습니까? (y/n)"
        read -r response

        if [[ "$response" =~ ^[Yy]$ ]]; then
            log_info "기존 프로세스 종료 중..."
            pkill -f "garame_manager" 2>/dev/null || true
            pkill -f "python.*main.py" 2>/dev/null || true
            sleep 2
        else
            log_info "종료합니다."
            exit 0
        fi
    fi
}

# Watchdog 확인
check_watchdog() {
    if pgrep -f "watchdog.py" > /dev/null; then
        log_info "Watchdog가 실행 중입니다."
        return 0
    fi
    return 1
}

# 가상환경 활성화
activate_virtual_env() {
    log_info "가상환경 활성화 중..."
    source venv/bin/activate
    log_success "가상환경 활성화 완료"
}

# 환경 변수 설정
setup_environment() {
    # DISPLAY 설정 (GUI 실행을 위해)
    if [ -z "$DISPLAY" ]; then
        export DISPLAY=:0
    fi

    # Python 경로 설정
    export PYTHONPATH="$(pwd):$PYTHONPATH"

    # OpenCV 설정
    export OPENCV_VIDEOIO_PRIORITY_MSMF=0

    log_success "환경 변수 설정 완료"
}

# 로그 디렉토리 정리 (선택)
cleanup_logs() {
    if [ -d "logs" ]; then
        # 30일 이상 된 로그 파일 수 확인 (삭제 대상)
        old_log_count=$(find logs -name "*.log" -mtime +30 2>/dev/null | wc -l)

        # 삭제 대상이 있을 때만 질문
        if [ "$old_log_count" -gt 0 ]; then
            log_warning "30일 이상 된 로그 파일이 $old_log_count 개 있습니다."
            log_info "삭제하시겠습니까? (y/n)"
            read -r response

            if [[ "$response" =~ ^[Yy]$ ]]; then
                find logs -name "*.log" -mtime +30 -delete 2>/dev/null || true
                log_success "오래된 로그 파일 삭제 완료"
            fi
        fi
    fi
}

# Watchdog와 함께 실행
run_with_watchdog() {
    log_info "Watchdog 모드로 실행 중..."

    # 로그 디렉토리 생성
    mkdir -p logs

    # 오래된 PID 및 signal 파일 정리
    if [ -f "watchdog.pid" ]; then
        OLD_PID=$(cat watchdog.pid 2>/dev/null)
        if [ ! -z "$OLD_PID" ]; then
            if ! ps -p "$OLD_PID" > /dev/null 2>&1; then
                log_info "오래된 watchdog.pid 파일 삭제 (프로세스 $OLD_PID 없음)"
                rm -f watchdog.pid
                # 관련 signal 파일도 정리
                rm -f normal_exit.signal watchdog_exit.signal restart.signal 2>/dev/null || true
            fi
        else
            rm -f watchdog.pid
            rm -f normal_exit.signal watchdog_exit.signal restart.signal 2>/dev/null || true
        fi
    fi

    # Watchdog가 이미 실행 중인지 확인
    if check_watchdog; then
        # 자동 시작 모드면 대화형 프롬프트 생략
        if [ "${AUTO_MODE:-false}" = "true" ]; then
            log_info "Watchdog가 이미 실행 중입니다. 유지합니다."
            # Watchdog는 있지만 Manager가 없으면 시작
            if ! pgrep -f "garame_manager\|python.*main.py" > /dev/null; then
                log_info "Manager 프로그램 시작 중..."

                # 가상환경 활성화
                if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
                    source venv/bin/activate
                fi

                if [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
                    nohup ./garame_manager --config config.conf > logs/manager_$(date +%Y%m%d_%H%M%S).log 2>&1 &
                elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
                    nohup ./garame_manager --config config.conf > logs/manager_$(date +%Y%m%d_%H%M%S).log 2>&1 &
                elif [ -f "main.py" ]; then
                    nohup python3 main.py --config config.conf > logs/manager_$(date +%Y%m%d_%H%M%S).log 2>&1 &
                fi
                sleep 2
                log_success "Manager 프로그램 시작 완료"
            fi
            return
        fi

        log_warning "Watchdog가 이미 실행 중입니다."
        log_info "기존 Watchdog를 종료하고 다시 시작하시겠습니까? (y/n)"
        read -r response

        if [[ "$response" =~ ^[Yy]$ ]]; then
            log_info "기존 Watchdog 종료 중..."
            pkill -f "watchdog.py" || true
            sleep 2
        else
            log_info "기존 Watchdog를 유지합니다."
            # Watchdog는 있지만 Manager가 없으면 시작
            if ! pgrep -f "garame_manager\|python.*main.py" > /dev/null; then
                log_info "Manager 프로그램 시작 중..."

                # 가상환경 활성화
                if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
                    source venv/bin/activate
                fi

                if [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
                    nohup ./garame_manager --config config.conf > logs/manager_$(date +%Y%m%d_%H%M%S).log 2>&1 &
                elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
                    nohup ./garame_manager --config config.conf > logs/manager_$(date +%Y%m%d_%H%M%S).log 2>&1 &
                elif [ -f "main.py" ]; then
                    nohup python3 main.py --config config.conf > logs/manager_$(date +%Y%m%d_%H%M%S).log 2>&1 &
                fi
                sleep 2
                log_success "Manager 프로그램 시작 완료"
            fi
            return
        fi
    fi

    # Watchdog 실행
    if [ -f "watchdog.py" ]; then
        log_info "Watchdog 시작 중..."

        # 가상환경 활성화
        if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        fi

        nohup python3 watchdog.py > logs/watchdog.log 2>&1 &
        WATCHDOG_PID=$!

        sleep 2

        if ps -p $WATCHDOG_PID > /dev/null; then
            log_success "Watchdog 시작 완료 (PID: $WATCHDOG_PID)"
            log_info "Watchdog가 프로그램을 모니터링합니다."

            # Manager 프로그램 시작
            # 가상환경 활성화
            if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
                source venv/bin/activate
            fi

            if [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
                log_info "Manager 프로그램 시작 중 (실행 파일 모드)..."
                LOG_FILE="logs/manager_$(date +%Y%m%d_%H%M%S).log"
                nohup ./garame_manager --config config.conf > "$LOG_FILE" 2>&1 &
                MANAGER_PID=$!
                sleep 3

                if pgrep -f "garame_manager" > /dev/null; then
                    log_success "Manager 프로그램 시작 완료"
                    log_info "Watchdog가 Manager를 모니터링합니다."
                    log_info "프로그램이 종료되면 자동으로 재시작됩니다."
                else
                    log_error "Manager 프로그램 시작 실패"
                    log_error "로그 파일을 확인하세요: $LOG_FILE"

                    # 마지막 10줄 출력
                    if [ -f "$LOG_FILE" ]; then
                        echo ""
                        log_error "=== 오류 로그 마지막 10줄 ==="
                        tail -n 10 "$LOG_FILE"
                        echo ""

                        # cv2 오류 확인
                        if grep -q "No module named 'cv2'" "$LOG_FILE"; then
                            log_error "cv2 모듈 오류가 감지되었습니다!"
                            log_info "해결 방법:"
                            log_info "  1. CV2_TROUBLESHOOTING.md 참조"
                            log_info "  2. 새 소스로 재빌드 필요 (manager_1.9.3_source_cv2_enhanced.tar.gz)"
                            log_info "  3. 상세 가이드: cat CV2_TROUBLESHOOTING.md"
                        fi
                    fi
                fi
            elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
                log_info "Manager 프로그램 시작 중 (실행 파일 모드 --onefile)..."
                LOG_FILE="logs/manager_$(date +%Y%m%d_%H%M%S).log"
                nohup ./garame_manager --config config.conf > "$LOG_FILE" 2>&1 &
                MANAGER_PID=$!
                sleep 3

                if pgrep -f "garame_manager" > /dev/null; then
                    log_success "Manager 프로그램 시작 완료"
                    log_info "Watchdog가 Manager를 모니터링합니다."
                    log_info "프로그램이 종료되면 자동으로 재시작됩니다."
                else
                    log_error "Manager 프로그램 시작 실패"
                    log_error "로그 파일을 확인하세요: $LOG_FILE"

                    # 마지막 10줄 출력
                    if [ -f "$LOG_FILE" ]; then
                        echo ""
                        log_error "=== 오류 로그 마지막 10줄 ==="
                        tail -n 10 "$LOG_FILE"
                        echo ""

                        # cv2 오류 확인
                        if grep -q "No module named 'cv2'" "$LOG_FILE"; then
                            log_error "cv2 모듈 오류가 감지되었습니다!"
                            log_info "해결 방법:"
                            log_info "  1. CV2_TROUBLESHOOTING.md 참조"
                            log_info "  2. 새 소스로 재빌드 필요 (manager_1.9.3_source_cv2_enhanced.tar.gz)"
                            log_info "  3. 상세 가이드: cat CV2_TROUBLESHOOTING.md"
                        fi
                    fi
                fi
            elif [ -f "main.py" ]; then
                log_info "Manager 프로그램 시작 중 (Python 모드)..."
                LOG_FILE="logs/manager_$(date +%Y%m%d_%H%M%S).log"
                nohup python3 main.py --config config.conf > "$LOG_FILE" 2>&1 &
                MANAGER_PID=$!
                sleep 3

                if pgrep -f "python.*main.py" > /dev/null; then
                    log_success "Manager 프로그램 시작 완료"
                    log_info "Watchdog가 Manager를 모니터링합니다."
                    log_info "프로그램이 종료되면 자동으로 재시작됩니다."
                else
                    log_error "Manager 프로그램 시작 실패"
                    log_error "로그 파일을 확인하세요: $LOG_FILE"

                    # 마지막 10줄 출력
                    if [ -f "$LOG_FILE" ]; then
                        echo ""
                        log_error "=== 오류 로그 마지막 10줄 ==="
                        tail -n 10 "$LOG_FILE"
                        echo ""
                    fi
                fi
            else
                log_error "garame_manager 또는 main.py 파일을 찾을 수 없습니다."
            fi
        else
            log_error "Watchdog 시작 실패"
            log_info "일반 모드로 실행합니다..."
            run_normal
        fi
    else
        log_warning "watchdog.py 파일을 찾을 수 없습니다."
        log_info "일반 모드로 실행합니다..."
        run_normal
    fi
}

# 일반 실행
run_normal() {
    log_info "프로그램 실행 중..."

    # PyInstaller 빌드 실행 파일이 있으면 우선 사용 (--onefile 모드)
    if [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
        log_info "실행 파일 모드: ./garame_manager"
        ./garame_manager "$@"
    # 없으면 Python으로 실행 (가상환경 활성화)
    elif [ -f "main.py" ]; then
        log_info "Python 모드: python3 main.py"

        # 가상환경 활성화
        if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
            log_info "가상환경 활성화 중..."
            source venv/bin/activate
        fi

        python3 main.py "$@"
    else
        log_error "실행 파일(garame_manager) 또는 main.py를 찾을 수 없습니다."
        exit 1
    fi
}

# 백그라운드 실행
run_background() {
    log_info "백그라운드 모드로 실행 중..."

    # 로그 파일 준비
    mkdir -p logs
    LOG_FILE="logs/manager_$(date +%Y%m%d_%H%M%S).log"

    # 백그라운드 실행 (실행 파일 우선)
    if [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
        log_info "실행 파일 모드로 시작 (--onedir)..."
        nohup ./garame_manager > "$LOG_FILE" 2>&1 &
        MANAGER_PID=$!
    elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
        log_info "실행 파일 모드로 시작 (--onefile)..."
        nohup ./garame_manager > "$LOG_FILE" 2>&1 &
        MANAGER_PID=$!
    elif [ -f "main.py" ]; then
        log_info "Python 모드로 시작..."

        # 가상환경 활성화
        if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        fi

        nohup python3 main.py > "$LOG_FILE" 2>&1 &
        MANAGER_PID=$!
    else
        log_error "garame_manager 또는 main.py를 찾을 수 없습니다."
        exit 1
    fi

    sleep 2

    if ps -p $MANAGER_PID > /dev/null; then
        log_success "프로그램이 백그라운드에서 실행 중입니다 (PID: $MANAGER_PID)"
        log_info "로그 파일: $LOG_FILE"
        log_info "프로그램 종료: kill $MANAGER_PID"
    else
        log_error "프로그램 시작 실패"
        log_info "로그를 확인하세요: $LOG_FILE"
        exit 1
    fi
}

# 디버그 모드 실행
run_debug() {
    log_info "디버그 모드로 실행 중..."

    # 환경 변수 설정
    export PYTHONUNBUFFERED=1
    export DEBUG=1

    # 상세 로그 출력 (실행 파일 우선)
    if [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
        log_info "실행 파일 모드 (디버그 --onedir)..."
        ./garame_manager
    elif [ -f "garame_manager" ] && [ -x "garame_manager" ]; then
        log_info "실행 파일 모드 (디버그 --onefile)..."
        ./garame_manager
    elif [ -f "main.py" ]; then
        log_info "Python 모드 (디버그)..."

        # 가상환경 활성화
        if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        fi

        python3 -u main.py
    else
        log_error "garame_manager 또는 main.py를 찾을 수 없습니다."
        exit 1
    fi
}

# 사용법 출력
print_usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  (없음)      - 일반 모드로 실행"
    echo "  -w, --watchdog  - Watchdog 모드로 실행 (자동 재시작)"
    echo "  -b, --background - 백그라운드로 실행"
    echo "  -d, --debug      - 디버그 모드로 실행"
    echo "  -s, --stop       - 실행 중인 프로그램 종료"
    echo "  -h, --help       - 도움말 출력"
    echo ""
    echo "예제:"
    echo "  $0                  # 일반 실행"
    echo "  $0 -w               # Watchdog와 함께 실행"
    echo "  $0 -b               # 백그라운드 실행"
    echo "  $0 -d               # 디버그 모드"
    echo "  $0 -s               # 프로그램 종료"
    echo ""
}

# 프로그램 종료
stop_program() {
    log_info "실행 중인 프로그램 종료 중..."

    # Manager 종료 (실행 파일 + Python)
    MANAGER_STOPPED=false
    if pgrep -f "garame_manager" > /dev/null; then
        pkill -f "garame_manager"
        MANAGER_STOPPED=true
    fi
    if pgrep -f "python.*main.py" > /dev/null; then
        pkill -f "python.*main.py"
        MANAGER_STOPPED=true
    fi

    if [ "$MANAGER_STOPPED" = true ]; then
        log_success "Manager 종료 완료"
    else
        log_info "실행 중인 Manager가 없습니다."
    fi

    # Watchdog 종료
    if pgrep -f "watchdog.py" > /dev/null; then
        pkill -f "watchdog.py"
        log_success "Watchdog 종료 완료"
    fi

    log_success "모든 프로그램 종료 완료"
}

################################################################################
# 메인 실행
################################################################################

main() {
    print_banner

    # 자동 시작 모드 확인 (환경 변수 또는 인수)
    if [ "${1:-}" = "auto" ] || [ "${AUTOSTART:-}" = "true" ]; then
        export AUTO_MODE=true
        MODE="watchdog"  # 자동 시작 시 watchdog 모드로 실행
        log_info "자동 시작 모드 (Watchdog 활성화)"
    else
        # 명령행 인수 처리
        case "${1:-}" in
            -h|--help)
                print_usage
                exit 0
                ;;
            -s|--stop)
                stop_program
                exit 0
                ;;
            -w|--watchdog)
                MODE="watchdog"
                ;;
            -b|--background)
                MODE="background"
                ;;
            -d|--debug)
                MODE="debug"
                ;;
            "")
                MODE="watchdog"  # 기본값을 watchdog로 변경
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                print_usage
                exit 1
                ;;
        esac
    fi

    # 사전 검사
    check_python
    check_virtual_env
    check_running_process

    # 가상환경 활성화
    activate_virtual_env

    # 환경 설정
    setup_environment

    # 로그 정리 (선택)
    cleanup_logs

    # 모드별 실행
    case "$MODE" in
        watchdog)
            run_with_watchdog
            ;;
        background)
            run_background
            ;;
        debug)
            run_debug
            ;;
        normal)
            run_normal
            ;;
    esac
}

# 스크립트 실행
main "$@"
