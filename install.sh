#!/usr/bin/env bash
# 작성자: Git 이력 참조
# 작성목적: pdf-design 저장소를 Claude Code·Codex 스킬 폴더에 심볼릭 링크로 연결한다.
# 작성일: 2026-09-17
# 주의사항:
#   - 링크 방식이라 저장소를 수정하거나 git pull 하면 두 도구에 즉시 반영된다.
#   - 대상 경로에 링크가 아닌 실제 폴더가 있으면 덮어쓰지 않고 중단한다.
#   - Codex 경로는 CODEX_HOME 이 있으면 그것을 따른다.
# 사용법: ./install.sh [--uninstall]
# 변경사항 내역:
# - 2026-09-17 | 최초 작성 | Claude Code·Codex 링크 설치/제거
set -euo pipefail

SKILL_NAME="pdf-design"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_ROOTS=(
  "${HOME}/.claude/skills"
  "${CODEX_HOME:-${HOME}/.codex}/skills"
)

uninstall=false
if [[ "${1:-}" == "--uninstall" ]]; then
  uninstall=true
fi

for root in "${TARGET_ROOTS[@]}"; do
  target="${root}/${SKILL_NAME}"
  if [[ "${uninstall}" == true ]]; then
    if [[ -L "${target}" ]]; then
      rm "${target}"
      echo "제거: ${target}"
    fi
    continue
  fi

  mkdir -p "${root}"
  if [[ -e "${target}" && ! -L "${target}" ]]; then
    echo "중단: ${target} 에 링크가 아닌 폴더가 있습니다. 확인 후 직접 옮기거나 지워 주세요." >&2
    exit 1
  fi
  ln -sfn "${REPO_DIR}" "${target}"
  echo "연결: ${target} -> ${REPO_DIR}"
done

if [[ "${uninstall}" == false ]]; then
  command -v pdftoppm >/dev/null || echo "참고: pdftoppm 이 없어 미리보기·갤러리를 쓸 수 없습니다 (macOS: brew install poppler)"
fi
