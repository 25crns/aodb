#!/usr/bin/env bash
# Loads all required SQL scripts into ANY MySQL server (local or cloud), in the right order.
# Usage:  ./database/load_db.sh HOST PORT USER [CA_FILE]
#   local : ./database/load_db.sh localhost 3306 root
#   Aiven : ./database/load_db.sh my-mysql.aivencloud.com 12345 avnadmin ca.pem
# Optional: export MYSQL_PWD='password' first to avoid the prompt.
HOST=${1:?host required}; PORT=${2:-3306}; DBUSER=${3:-root}; CA=${4:-}
if [ -z "$MYSQL_PWD" ]; then read -r -s -p "Password for $DBUSER@$HOST: " MYSQL_PWD; echo; export MYSQL_PWD; fi
SSL=()
if [ -n "$CA" ]; then CA=$(realpath "$CA"); SSL=(--ssl-mode=VERIFY_CA --ssl-ca="$CA"); fi
cd "$(dirname "$0")" || exit 1
for f in 01_create_database 02_create_tables 03_insert_data 05_views 07_triggers 06_transactions 09_auth; do
  echo ">> $f.sql"
  mysql -h "$HOST" -P "$PORT" -u "$DBUSER" "${SSL[@]}" < "$f.sql" || { echo "FAILED at $f.sql"; exit 1; }
done
echo "Done. Now run:  python seed_users.py"
