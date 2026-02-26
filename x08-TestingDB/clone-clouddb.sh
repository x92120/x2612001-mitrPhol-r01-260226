#!/bin/bash
# =============================================================================
# clone-clouddb.sh — Clone Cloud DB → Local Docker DB
# Usage: ./clone-clouddb.sh
# =============================================================================

set -e

# ── Config ────────────────────────────────────────────────────────────────────
CLOUD_HOST="152.42.166.150"
CLOUD_PORT="3306"
CLOUD_USER="mixingcontrol"
CLOUD_PASS="admin100"
CLOUD_DB="xMixingControl"

LOCAL_CONTAINER="xmixing-testing-db"
LOCAL_ROOT_PASS="admin100"
LOCAL_DB="xMixingControl"

DUMP_FILE="$(dirname "$0")/dump.sql"
COMPOSE_FILE="$(dirname "$0")/docker-compose.yml"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC}   $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERR]${NC}  $1"; exit 1; }

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║       Cloud DB  →  Local DB  Clone       ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""

# ── Step 1: Dump from cloud ───────────────────────────────────────────────────
info "Step 1/5 — Dumping from cloud DB (${CLOUD_HOST}:${CLOUD_PORT})..."
mysqldump --no-tablespaces \
  -h "$CLOUD_HOST" -P "$CLOUD_PORT" \
  -u "$CLOUD_USER" -p"$CLOUD_PASS" \
  "$CLOUD_DB" > "$DUMP_FILE" 2>/dev/null
LINES=$(wc -l < "$DUMP_FILE")
success "Dump saved: $DUMP_FILE (${LINES} lines)"

# ── Step 2: Stop local container ─────────────────────────────────────────────
info "Step 2/5 — Stopping local DB container..."
docker compose -f "$COMPOSE_FILE" stop testing-db 2>/dev/null || true
docker compose -f "$COMPOSE_FILE" rm -f testing-db 2>/dev/null || true
success "Container stopped and removed"

# ── Step 3: Wipe local data dir ───────────────────────────────────────────────
DATA_DIR="$(dirname "$0")/data"
info "Step 3/5 — Clearing local data directory (${DATA_DIR})..."
if [ -d "$DATA_DIR" ] && [ "$(ls -A "$DATA_DIR" 2>/dev/null)" ]; then
  sudo rm -rf "$DATA_DIR"/* "$DATA_DIR"/.[!.]* 2>/dev/null || true
  sudo chown -R "$(whoami):$(whoami)" "$DATA_DIR" 2>/dev/null || true
fi
mkdir -p "$DATA_DIR"
success "Data directory cleared"

# ── Step 4: Start fresh local container ───────────────────────────────────────
info "Step 4/5 — Starting fresh local DB container..."
docker compose -f "$COMPOSE_FILE" up -d testing-db 2>/dev/null

info "      Waiting for MariaDB to initialize..."
for i in $(seq 1 30); do
  if docker exec "$LOCAL_CONTAINER" mariadb -u root -p"$LOCAL_ROOT_PASS" -e "SELECT 1;" &>/dev/null; then
    success "MariaDB is ready (${i}s)"
    break
  fi
  if [ "$i" -eq 30 ]; then
    error "MariaDB did not start within 30 seconds. Check: docker logs ${LOCAL_CONTAINER}"
  fi
  sleep 1
done

# ── Step 5: Restore dump ──────────────────────────────────────────────────────
info "Step 5/5 — Restoring dump to local DB..."
docker exec -i "$LOCAL_CONTAINER" mariadb -u root -p"$LOCAL_ROOT_PASS" "$LOCAL_DB" < "$DUMP_FILE"
success "Restore complete"

# ── Start all services ────────────────────────────────────────────────────────
info "      Starting Adminer & phpMyAdmin..."
docker compose -f "$COMPOSE_FILE" up -d 2>/dev/null

# ── Summary ───────────────────────────────────────────────────────────────────
TABLE_COUNT=$(docker exec "$LOCAL_CONTAINER" mariadb -u root -p"$LOCAL_ROOT_PASS" "$LOCAL_DB" \
  -sN -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${LOCAL_DB}';" 2>/dev/null)

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║           ✅  Clone Complete!             ║${NC}"
echo -e "${GREEN}╠══════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  Tables restored : ${TABLE_COUNT}"
echo -e "${GREEN}║${NC}  Adminer         : http://localhost:8080"
echo -e "${GREEN}║${NC}  phpMyAdmin      : http://localhost:8081"
echo -e "${GREEN}╚══════════════════════════════════════════╝${NC}"
echo ""
