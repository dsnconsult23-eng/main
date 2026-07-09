#!/usr/bin/env bash
# Автоматски деплој на SigLife Reporting кон продукцискиот сервер.
# Употреба:  ./deploy.sh          (со потврда)
#            ./deploy.sh --yes    (без потврда, за скрипти/cron)
#
# Пренесува ги само релевантните runtime фајлови/папки (без venv,
# __pycache__, uploads, локални слики за тестирање), преку tar+ssh pipe
# (без потреба од rsync), и го рестартира systemd сервисот.

set -euo pipefail

SKIP_CONFIRM=0
for arg in "$@"; do
    case "$arg" in
        --yes|-y) SKIP_CONFIRM=1 ;;
    esac
done

REMOTE_USER_HOST="deploy@192.168.100.61"
REMOTE_PATH="/opt/siglife-reporting"
SERVICE_NAME="siglife-reporting.service"

# Кои патеки од локалниот проект се пренесуваат (runtime-релевантни).
PATHS_TO_DEPLOY=(
    main.py
    db_ifx.py
    requrements.txt
    routers
    templates
    auth
    Utils
    services
    static
)

cd "$(dirname "${BASH_SOURCE[0]}")"

echo "==> Локални промени (git status) во патеките што се деплојираат:"
echo "----------------------------------------------------------------"
git status --short -- "${PATHS_TO_DEPLOY[@]}" || true
echo "----------------------------------------------------------------"

if [ "$SKIP_CONFIRM" -eq 1 ]; then
    echo "==> --yes зададено, продолжувам без потврда."
else
    read -r -p "Продолжи со деплој кон ${REMOTE_USER_HOST}:${REMOTE_PATH}? [y/N] " CONFIRM
    case "$CONFIRM" in
        [yY]|[yY][eE][sS]) ;;
        *) echo "Прекинато."; exit 1 ;;
    esac
fi

echo "==> Пакувам и пренесувам фајлови кон ${REMOTE_USER_HOST}:${REMOTE_PATH} ..."
tar \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".git" \
    -czf - "${PATHS_TO_DEPLOY[@]}" \
    | ssh "${REMOTE_USER_HOST}" "tar -xzf - -C '${REMOTE_PATH}'"

echo "==> Рестартирам ${SERVICE_NAME} на серверот ..."
ssh "${REMOTE_USER_HOST}" "systemctl restart ${SERVICE_NAME} && systemctl is-active ${SERVICE_NAME}"

echo "==> Деплојот е завршен."
