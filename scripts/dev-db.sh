#!/usr/bin/env bash
# Base de pruebas temporal (PostgreSQL 17) para el entorno de desarrollo de Claude.
# En tu Mac usa tu Postgres local con las variables DATABASE_* del .env.
set -e
# Si corre como root, se ejecuta como el usuario pgdev (Postgres no arranca como root).
if [ "$(id -u)" = "0" ]; then exec runuser -u pgdev -- env NIDO_PG_DIR="${NIDO_PG_DIR:-/home/claude/pg17}" "$0" "$@"; fi
ROOT="${NIDO_PG_DIR:-$HOME/pg17}"
BIN=$(dirname "$(find "$ROOT/node_modules/@embedded-postgres" -name pg_ctl | head -1)")
PORT="${NIDO_PG_PORT:-55434}"
if [ ! -d "$ROOT/data" ]; then
  echo pw > "$ROOT/pw.txt"
  "$BIN/initdb" -D "$ROOT/data" -U nido --pwfile="$ROOT/pw.txt" -A scram-sha-256 -E UTF8 --locale=C.UTF-8 >/dev/null
fi
rm -f "$ROOT/data/postmaster.pid" 2>/dev/null || true
"$BIN/pg_ctl" -D "$ROOT/data" -o "-p $PORT -k /tmp -c listen_addresses=127.0.0.1" -l "$ROOT/pg.log" start >/dev/null 2>&1 || true
sleep 2
echo "postgresql+psycopg://nido:pw@127.0.0.1:$PORT/nidoguard_dev"
