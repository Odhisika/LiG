#!/usr/bin/env bash
set -euo pipefail

echo "=========================================="
echo "  LiG Security Audit"
echo "=========================================="
echo ""

# 1. Dependency vulnerability scan
echo "--- Dependency Vulnerabilities ---"
pip-audit || true
echo ""

# 2. Django deployment check
echo "--- Django Deployment Check ---"
python manage.py check --deploy 2>&1 | grep -v "^$" || true
echo ""

# 3. Django system check
echo "--- Django System Check ---"
python manage.py check 2>&1 | grep -v "^$"
echo ""

# 4. Check DEBUG mode
echo "--- DEBUG Mode Check ---"
DEBUG_VAL=$(python -c "from decouple import config; print(config('DEBUG', default=''))")
if [ "$DEBUG_VAL" = "True" ]; then
    echo "WARNING: DEBUG=True in environment"
else
    echo "OK: DEBUG=$DEBUG_VAL"
fi
echo ""

# 5. Check secret key length
echo "--- Secret Key Check ---"
SK_LEN=$(python -c "from decouple import config; print(len(config('SECRET_KEY', default='')))")
if [ "$SK_LEN" -ge 50 ]; then
    echo "OK: SECRET_KEY length = $SK_LEN"
else
    echo "WARNING: SECRET_KEY too short ($SK_LEN chars)"
fi
echo ""

echo "=========================================="
echo "  Audit complete"
echo "=========================================="
