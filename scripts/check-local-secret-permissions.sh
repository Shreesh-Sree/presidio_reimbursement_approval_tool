#!/usr/bin/env bash
set -euo pipefail

# This check deliberately never prints file contents or changes permissions.
# It catches the common shared-workstation mistake before local services start.
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
failed=0

while IFS= read -r -d '' secret_file; do
  mode="$(stat -c '%a' "$secret_file")"
  if [[ "${mode: -2}" != "00" ]]; then
    relative_path="${secret_file#"$repository_root"/}"
    echo "Local secret file must be owner-only (0600): $relative_path is mode $mode" >&2
    failed=1
  fi
done < <(
  find "$repository_root" -maxdepth 3 -type f \( \
    -name '.env' -o -name '.env.local' -o -name '.env.production' -o -name 'secrets.txt' \
  \) -print0
)

if (( failed )); then
  echo 'Set restrictive modes without printing values, for example: chmod 600 <affected-file>' >&2
  exit 1
fi

echo 'Local secret-file permissions: valid'
