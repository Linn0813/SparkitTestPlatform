# shellcheck shell=bash
# 被 dev/*.sh source，勿直接执行

set_env_kv() {
  local env_file="$1"
  local key="$2"
  local val="$3"
  if grep -q "^${key}=" "$env_file"; then
    if [[ "$(uname)" == "Darwin" ]]; then
      sed -i '' "s|^${key}=.*|${key}=${val}|" "$env_file"
    else
      sed -i "s|^${key}=.*|${key}=${val}|" "$env_file"
    fi
  else
    echo "${key}=${val}" >> "$env_file"
  fi
}

ensure_backend_env() {
  local root="$1"
  local env_file="$root/backend/.env"
  local example="$root/.env.example"
  if [[ ! -f "$env_file" ]]; then
    cp "$example" "$env_file"
    echo "已创建 backend/.env"
  fi
  echo "$env_file"
}
