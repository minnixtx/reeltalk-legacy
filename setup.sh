#!/usr/bin/env bash
# Generate the secrets ReelTalk needs and fill them into .env.
# Safe to re-run: values that are already set are never overwritten.
set -euo pipefail

ENV_FILE="${1:-.env}"

if [ ! -f "$ENV_FILE" ]; then
    echo "No $ENV_FILE found. Run: cp .env.example .env" >&2
    exit 1
fi

# --- helpers ---------------------------------------------------------------
get_var() { # get_var NAME -> current value (empty if unset)
    sed -n "s/^$1=//p" "$ENV_FILE" | tail -1
}

set_var() { # set_var NAME VALUE
    local tmp
    tmp="$(mktemp)"
    awk -v k="$1" -v v="$2" 'BEGIN{FS=OFS="="} $1==k{print k OFS v; next}{print}' \
        "$ENV_FILE" > "$tmp" && mv "$tmp" "$ENV_FILE"
}

gen_secret() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import secrets; print(secrets.token_urlsafe(50))'
    elif command -v openssl >/dev/null 2>&1; then
        openssl rand -hex 50
    else
        echo "Need python3 or openssl to generate secrets." >&2
        exit 1
    fi
}

prompt() { # prompt NAME [default] -> value (falls back to default when not a TTY)
    local name="$1" def="${2:-}" val=""
    if [ -t 0 ]; then
        read -r -p "$name${def:+ [$def]}: " val || val=""
    fi
    echo "${val:-$def}"
}

# --- DOMAIN -----------------------------------------------------------------
domain="$(get_var DOMAIN)"
if [ -z "$domain" ] || [ "$domain" = "your-instance.example.com" ]; then
    domain="$(prompt DOMAIN)"
    if [ -z "$domain" ]; then
        echo "DOMAIN is required (e.g. films.example.com). Set it in $ENV_FILE and re-run." >&2
        exit 1
    fi
    set_var DOMAIN "$domain"
fi

# --- secrets -----------------------------------------------------------------
for var in SECRET_KEY POSTGRES_PASSWORD REDIS_PASSWORD; do
    if [ -z "$(get_var "$var")" ]; then
        echo "Generating $var..."
        set_var "$var" "$(gen_secret)"
    else
        echo "$var already set, skipping."
    fi
done

echo
echo "Done. Next steps:"
echo "  1. Review $ENV_FILE (DOMAIN and the generated secrets)."
echo "  2. docker compose up -d --build"
echo "  3. The site is now reachable at http://<host>:3030 (plain HTTP);"
echo "     terminate TLS with your own reverse proxy in front of that port."
