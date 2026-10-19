#!/bin/bash
# Compatible with the Bash 3.2 shipped with macOS.
set -euo pipefail

project_root="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
backend_dir="$project_root/backend"
frontend_dir="$project_root/frontend"
backend_python="$backend_dir/.venv/bin/python"
frontend_url="http://127.0.0.1:5173"
backend_url="http://127.0.0.1:8000"

fail() {
    printf '[ERROR] %s\n' "$*" >&2
    exit 1
}

[[ -d "$backend_dir" && -f "$frontend_dir/package.json" ]] ||
    fail "Cannot find backend/ and frontend/ next to start_mac.sh."
[[ -x "$backend_python" ]] ||
    fail "Missing macOS virtual environment. Run: cd backend && python3 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"

if ! "$backend_python" -c 'import sys; raise SystemExit(sys.prefix == sys.base_prefix)'; then
    fail "Cannot use backend/.venv. Recreate it on this Mac; Windows virtual environments cannot be reused."
fi
if ! "$backend_python" -c 'import fastapi, uvicorn, sqlalchemy, pymysql, httpx, aiotieba'; then
    fail "Missing backend dependencies. Run backend/.venv/bin/python -m pip install -r backend/requirements.txt from the project root."
fi

for tool in node npm curl; do
    command -v "$tool" >/dev/null 2>&1 || fail "Missing $tool. See the first-time macOS setup in README.md."
done
[[ -f "$frontend_dir/node_modules/vite/bin/vite.js" ]] ||
    fail "Missing frontend dependencies. Run: cd frontend && npm ci"
if ! (cd "$frontend_dir" && npm ls --depth=0 >/dev/null 2>&1); then
    fail "Frontend dependencies are incomplete. Run: cd frontend && npm ci"
fi

# Check before starting either service. Do not stop an existing port owner.
"$backend_python" - <<'PY'
import socket
import sys

for port in (8000, 5173):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("127.0.0.1", port))
        except OSError as exc:
            print(f"[ERROR] Port {port} is unavailable: {exc}. Stop its existing service and retry.", file=sys.stderr)
            sys.exit(1)
PY

backend_pid=""
frontend_pid=""
stop_status=0

cleanup() {
    local status=$?
    local service_pid
    local groups_alive
    local deadline
    if [[ "$stop_status" -ne 0 ]]; then
        status=$stop_status
    fi
    trap - EXIT
    trap '' INT TERM HUP
    set +e

    printf '\nStopping frontend and backend...\n'
    # Job control gives each service its own process group. Include reloaders
    # and Vite helpers even if their original parent has already exited.
    for service_pid in "$frontend_pid" "$backend_pid"; do
        if [[ -n "$service_pid" ]]; then
            kill -TERM -- "-$service_pid" 2>/dev/null
        fi
    done
    deadline=$((SECONDS + 5))
    while (( SECONDS < deadline )); do
        groups_alive=0
        for service_pid in "$frontend_pid" "$backend_pid"; do
            if [[ -n "$service_pid" ]] && kill -0 -- "-$service_pid" 2>/dev/null; then
                groups_alive=1
            fi
        done
        [[ "$groups_alive" -eq 0 ]] && break
        sleep 0.2
    done
    for service_pid in "$frontend_pid" "$backend_pid"; do
        if [[ -n "$service_pid" ]]; then
            kill -KILL -- "-$service_pid" 2>/dev/null
            wait "$service_pid" 2>/dev/null
        fi
    done
    exit "$status"
}

check_stop() {
    if [[ "$stop_status" -ne 0 ]]; then
        exit "$stop_status"
    fi
}

check_services() {
    kill -0 "$backend_pid" 2>/dev/null || fail "Backend exited. Check its output above."
    kill -0 "$frontend_pid" 2>/dev/null || fail "Frontend exited. Check its output above."
}

trap cleanup EXIT
# Record the request first so a signal between launch and PID assignment does
# not leave an untracked service behind.
trap 'stop_status=130' INT
trap 'stop_status=143' TERM
trap 'stop_status=129' HUP
set -m

check_stop
printf 'Starting backend: %s\n' "$backend_url"
(
    cd "$backend_dir"
    exec "$backend_python" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
) </dev/null &
backend_pid=$!

check_stop
printf 'Starting frontend: %s\n' "$frontend_url"
(
    cd "$frontend_dir"
    # Start Vite directly so its process group contains no npm wrapper.
    exec node node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
) </dev/null &
frontend_pid=$!

printf 'Waiting for both services (up to 120 seconds)...\n'
ready=0
deadline=$((SECONDS + 120))
while (( SECONDS < deadline )); do
    check_stop
    check_services
    if curl --noproxy '*' --fail --silent --max-time 1 "$backend_url/health" >/dev/null 2>&1 &&
        curl --noproxy '*' --fail --silent --max-time 1 "$frontend_url/" >/dev/null 2>&1; then
        check_stop
        check_services
        ready=1
        break
    fi
    sleep 1
done
readiness_status=$?
# With job control, an interrupted foreground probe can end the loop without
# invoking this shell's INT trap. Preserve that status instead of reporting a timeout.
check_stop
[[ "$readiness_status" -eq 0 ]] || exit "$readiness_status"
[[ "$ready" -eq 1 ]] || fail "Services did not become ready within 120 seconds. Check their output and backend/.env."

printf '\nFrontend: %s\nBackend:  %s\nPress Ctrl+C in this terminal to stop both services.\n' "$frontend_url" "$backend_url"
if ! /usr/bin/open "$frontend_url"; then
    printf '[WARN] Could not open the browser. Open %s manually.\n' "$frontend_url" >&2
fi

# Bash 3.2 has no wait -n. Keep supervising both services after startup.
while :; do
    check_stop
    check_services
    sleep 1
done
supervision_status=$?
check_stop
exit "$supervision_status"
