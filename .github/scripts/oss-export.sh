#!/usr/bin/env bash
# ==============================================================================
# oss-export.sh — Export open-core blobs from a private Git monorepo to an OSS
# target directory. Exports ONLY blobs tracked at a specified Git commit/ref
# (never the working tree), applies an allowlist + denylist, rejects symlinks /
# submodules / path traversal, reconciles the target (deleting stale content),
# and supports a safe dry-run mode that makes zero writes to target.
#
# Allowlist entries can be:
#   1. A simple path/glob — exported AS-IS to the same relative path.
#   2. A mapping:  private_source => public_destination
#      The source is resolved in the private monorepo; the destination is
#      the path in the OSS repo. Mappings enable canonical public-root assets
#      (e.g. README.md, .gitignore) that differ from the private monorepo's
#      root versions.
#
# Dependencies: git, rsync, realpath (all in standard CI runners).
# No non-stdlib Python packages required.
# ==============================================================================
set -euo pipefail

DRY_RUN=false
REF="HEAD"
SOURCE=""
TARGET=""
ALLOWLIST=""
DENYLIST=""
STAGING_DIR=""

usage() {
  echo "Usage: $0 [--ref REF] [--source DIR] [--target DIR] [--dry-run]" >&2
  exit 2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --ref)      REF="$2"; shift 2 ;;
    --source)   SOURCE="$2"; shift 2 ;;
    --target)   TARGET="$2"; shift 2 ;;
    --dry-run)  DRY_RUN=true; shift ;;
    --help|-h)  usage ;;
    *) echo "Unknown: $1" >&2; usage ;;
  esac
done

# ---- resolve directories ------------------------------------------------
[[ -z "$SOURCE" ]] && SOURCE="$(git rev-parse --show-toplevel)"
SOURCE="$(realpath "$SOURCE")"

# Target is required
: "${TARGET:?ERROR: --target is required}"
TARGET="$(realpath -m "$TARGET")"

# Target must NOT be inside source
[[ "$TARGET" == "$SOURCE" || "$TARGET" == "$SOURCE"/* ]] && {
  echo "ERROR: --target must NOT be inside --source" >&2
  exit 1
}

ALLOWLIST="${SOURCE}/.github/oss-export-allowlist.txt"
DENYLIST="${SOURCE}/.github/oss-export-denylist.txt"
STAGING_DIR="$(mktemp -d)"
trap "rm -rf '$STAGING_DIR'" EXIT

# ---- validate inputs ----------------------------------------------------
for f in "$ALLOWLIST" "$DENYLIST"; do
  [[ -f "$f" ]] || { echo "ERROR: $f not found" >&2; exit 1; }
done

git -C "$SOURCE" rev-parse --verify "${REF}^{commit}" >/dev/null 2>&1 || {
  echo "ERROR: Git ref '$REF' does not resolve to a commit" >&2
  exit 1
}

# ---- parse allowlist ----------------------------------------------------
# ALLOWED_RAW   — raw entries for validation (simple paths and mapping strings)
# ALLOWED_SRC   — list of simple (non-mapped) source patterns for git ls-tree
# MAPPINGS      — associative array: private_source -> public_destination
# MAPPING_DSTS  — set of mapped destination paths (for collision detection)
ALLOWED_RAW=()
ALLOWED_SRC=()
declare -A MAPPINGS
declare -A MAPPING_DSTS

while IFS= read -r line; do
  line="${line%%#*}"
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" ]] && continue
  ALLOWED_RAW+=("$line")

  # Check for mapping syntax:  private_source => public_destination
  if [[ "$line" == *"=>"* ]]; then
    # Reject malformed multiple '=>' tokens
    if [[ "$(echo "$line" | tr -cd '>' | wc -c)" != "$(echo "$line" | tr -cd '=' | wc -c)" ]] || \
       [[ "$line" == *"=>"*"=>"* ]]; then
      echo "ERROR: Malformed mapping (multiple '=>' tokens): $line" >&2
      exit 1
    fi

    # Split on '=>' with optional whitespace
    src="$(echo "$line" | sed -E 's/^[[:space:]]*//; s/[[:space:]]*=>.*//')"
    dst="$(echo "$line" | sed -E 's/.*=>[[:space:]]*//; s/[[:space:]]*$//')"

    # Validate source
    if [[ "$src" == /* ]]; then
      echo "ERROR: Absolute source path in mapping: $line" >&2; exit 1
    fi
    if [[ "$src" == *".."* ]]; then
      echo "ERROR: Traversal in mapping source: $line" >&2; exit 1
    fi
    if [[ -z "$src" ]]; then
      echo "ERROR: Empty source in mapping: $line" >&2; exit 1
    fi

    # Validate destination
    if [[ "$dst" == /* ]]; then
      echo "ERROR: Absolute destination path in mapping: $line" >&2; exit 1
    fi
    if [[ "$dst" == *".."* ]]; then
      echo "ERROR: Traversal in mapping destination: $line" >&2; exit 1
    fi
    if [[ -z "$dst" ]]; then
      echo "ERROR: Empty destination in mapping: $line" >&2; exit 1
    fi

    # Strict public metadata contract. Keep mapped source/destination pairs
    # explicit so private-repository metadata cannot be relocated into the
    # public repository. In particular, public CI must come from its dedicated
    # open-core template, never from the private monorepo workflow.
    case "${src}=>${dst}" in
      ".github/oss-root/README.md=>README.md"|\
      ".github/oss-root/.gitignore=>.gitignore"|\
      ".github/oss-root/LICENSE=>LICENSE"|\
      ".github/oss-root/workflows/ci.yml=>.github/workflows/ci.yml")
        ;;
      *)
        echo "ERROR: Mapping is not an approved public metadata pair: '$line'" >&2
        exit 1
        ;;
    esac

    # Reject duplicate destination (independent of manifest order)
    if [[ -n "${MAPPING_DSTS[$dst]:-}" ]]; then
      echo "ERROR: Duplicate mapping destination '$dst' (already mapped from '${MAPPING_DSTS[$dst]}')" >&2
      exit 1
    fi

    # Reject duplicate source (independent of manifest order)
    if [[ -n "${MAPPINGS[$src]:-}" ]]; then
      echo "ERROR: Duplicate mapping source '$src' (already maps to '${MAPPINGS[$src]}')" >&2
      exit 1
    fi

    # Reject destination that collides with a simple path
    for s in "${ALLOWED_SRC[@]}"; do
      if [[ "$s" == "$dst" || "$s" == "$dst/" || "$dst" == "$s"/* ]]; then
        echo "ERROR: Mapping destination '$dst' collides with simple path '$s'" >&2
        exit 1
      fi
    done

    # Reject path/tree overlap: source or destination overlaps with
    # any already-registered mapping (source-source, source-dst, dst-dst)
    for existing_src in "${!MAPPINGS[@]}"; do
      existing_dst="${MAPPINGS[$existing_src]}"
      # Source overlaps with existing source
      if [[ "$src" == "$existing_src" || "$src" == "$existing_src"/* || "$existing_src" == "$src"/* ]]; then
        echo "ERROR: Mapping source '$src' overlaps with existing source '$existing_src'" >&2
        exit 1
      fi
      # Source overlaps with existing destination
      if [[ "$src" == "$existing_dst" || "$src" == "$existing_dst"/* || "$existing_dst" == "$src"/* ]]; then
        echo "ERROR: Mapping source '$src' overlaps with existing destination '$existing_dst'" >&2
        exit 1
      fi
      # Destination overlaps with existing source
      if [[ "$dst" == "$existing_src" || "$dst" == "$existing_src"/* || "$existing_src" == "$dst"/* ]]; then
        echo "ERROR: Mapping destination '$dst' overlaps with existing source '$existing_src'" >&2
        exit 1
      fi
    done

    MAPPINGS["$src"]="$dst"
    MAPPING_DSTS["$dst"]="$src"
  else
    # Simple path entry
    if [[ "$line" == /* ]]; then
      echo "ERROR: Absolute path in allowlist: $line" >&2; exit 1
    fi
    if [[ "$line" == *".."* ]]; then
      echo "ERROR: Traversal in allowlist: $line" >&2; exit 1
    fi

    # Check for collisions with any already-registered mapping destination
    if [[ -n "${MAPPING_DSTS[$line]:-}" ]]; then
      echo "ERROR: Simple path '$line' collides with mapping destination (source: ${MAPPING_DSTS[$line]})" >&2
      exit 1
    fi

    ALLOWED_SRC+=("$line")
  fi
done < "$ALLOWLIST"

# Also check mapped sources against simple-path collisions (source overlaps)
for msrc in "${!MAPPINGS[@]}"; do
  for s in "${ALLOWED_SRC[@]}"; do
    if [[ "$msrc" == "$s" || "$msrc" == "$s"/* || "$s" == "$msrc"/* ]]; then
      echo "ERROR: Mapping source '$msrc' collides with simple path '$s'" >&2
      exit 1
    fi
  done
done

[[ ${#ALLOWED_RAW[@]} -gt 0 ]] || { echo "ERROR: Allowlist is empty" >&2; exit 1; }

# ---- parse denylist -----------------------------------------------------
DENIED=()
while IFS= read -r line; do
  line="${line%%#*}"
  line="${line#"${line%%[![:space:]]*}"}"
  line="${line%"${line##*[![:space:]]}"}"
  [[ -z "$line" ]] && continue
  DENIED+=("$line")
done < "$DENYLIST"

# ---- helper: match a gitpath against a gitwildmatch pattern ------------
# Pure bash glob-matching approximating gitwildmatch semantics.
# Returns 0 (match) or 1 (no match).
match_pattern() {
  local path="$1" pattern="$2"

  # Exact match
  [[ "$path" == "$pattern" ]] && return 0

  # Plain '**' matches everything
  [[ "$pattern" == "**" ]] && return 0

  # Leading '**/' means "match at any depth"
  if [[ "$pattern" == \*\*/* ]]; then
    local sub="${pattern#\*\*/}"
    # **/AUDIT.md → matches AUDIT.md or foo/AUDIT.md or a/b/AUDIT.md
    [[ "$path" == "$sub" || "$path" == */"$sub" ]] && return 0
    # **/internal_docs/** → matches anything under internal_docs/
    if [[ "$sub" == */ ]]; then
      [[ "$path" == "$sub"* || "$path" == */"$sub"* ]] && return 0
    fi
  fi

  # Trailing '/**' means "this dir and everything under it"
  if [[ "$pattern" == */\*\* ]]; then
    local prefix="${pattern%/\*\*}"
    [[ "$path" == "$prefix" || "$path" == "$prefix"/* ]] && return 0
  fi

  # For patterns with ** in the middle or other glob chars, use globstar.
  # Bash globstar (**) matches across / boundaries when enabled.
  if [[ "$pattern" == *\*\** || "$pattern" == *\** ]]; then
    shopt -s globstar
    [[ "$path" == $pattern ]] && return 0
  fi

  return 1
}

# ---- check if a path is denied -----------------------------------------
is_denied() {
  local path="$1"
  local p
  for p in "${DENIED[@]}"; do
    if match_pattern "$path" "$p"; then
      return 0
    fi
  done
  return 1
}

# ---- collect tracked files under each allowlist entry ------------------
# EXPORT_MAP:   destination_path -> source_path_at_ref
# Maps where each file should end up in the target (key = destination path,
# value = source git ref path).  For simple entries the two are the same;
# for mapped entries they differ.
declare -A EXPORT_MAP

echo "=== OSS Export ==="
echo "  Source     : ${SOURCE}"
echo "  Target     : ${TARGET}"
echo "  Ref        : ${REF}"
echo "  Allowlist  : ${ALLOWLIST}"
echo "  Denylist   : ${DENYLIST}"
echo "  Mode       : $( $DRY_RUN && echo "DRY-RUN" || echo "LIVE" )"
echo ""

# Count mappings safely (empty associative arrays trip set -u)
MAP_COUNT=0
set +u
MAP_COUNT=${#MAPPINGS[@]}
set -u
echo "  Mappings   : ${MAP_COUNT} entries"

EXPORT_COUNT=0
SKIP_COUNT=0

# ---- Phase 1: collect files from simple (non-mapped) entries -----------
for entry in "${ALLOWED_SRC[@]}"; do
  # Get tracked git objects under this tree at $REF
  # ls-tree gives: <mode> SP <type> SP <hash> TAB <path>
  while IFS=$'\t' read -r info gpath; do
    [[ -z "$gpath" ]] && continue
    # info looks like: "100644 blob abc123..."
    mode="${info%% *}"
    otype="${info#* }"; otype="${otype%% *}"

    # Reject symlinks (mode 120000)
    [[ "$mode" == "120000" ]] && {
      echo "SECURITY: Symlink rejected — ${gpath}" >&2
      exit 1
    }

    # Reject submodules (mode 160000, type commit)
    [[ "$mode" == "160000" || "$otype" == "commit" ]] && {
      echo "SECURITY: Submodule rejected — ${gpath}" >&2
      exit 1
    }

    # Reject path traversal in filename
    [[ "$gpath" == *".."* ]] && {
      echo "SECURITY: Path traversal rejected — ${gpath}" >&2
      exit 1
    }

    # Reject absolute paths
    [[ "$gpath" == /* ]] && {
      echo "SECURITY: Absolute path rejected — ${gpath}" >&2
      exit 1
    }

    # Check denylist
    if is_denied "$gpath"; then
      ((SKIP_COUNT+=1)) || true
      $DRY_RUN && echo "  SKIP (denylist): ${gpath}"
      continue
    fi

    # For simple entries: destination = source path
    EXPORT_MAP["$gpath"]="$gpath"
    ((EXPORT_COUNT+=1)) || true
    $DRY_RUN && echo "  EXPORT: ${gpath}"
  done < <(git -C "$SOURCE" ls-tree -r "$REF" -- "$entry")
done

# ---- Phase 2: collect files from mapped entries ------------------------
if [[ $MAP_COUNT -gt 0 ]]; then
for msrc in "${!MAPPINGS[@]}"; do
  mdst="${MAPPINGS[$msrc]}"

  # If the mapped source is a directory (trailing /), expand the tree
  if [[ "$msrc" == */ ]]; then
    while IFS=$'\t' read -r info gpath; do
      [[ -z "$gpath" ]] && continue
      mode="${info%% *}"
      otype="${info#* }"; otype="${otype%% *}"

      [[ "$mode" == "120000" ]] && {
        echo "SECURITY: Symlink rejected — ${gpath}" >&2; exit 1
      }
      [[ "$mode" == "160000" || "$otype" == "commit" ]] && {
        echo "SECURITY: Submodule rejected — ${gpath}" >&2; exit 1
      }
      [[ "$gpath" == *".."* ]] && {
        echo "SECURITY: Path traversal rejected — ${gpath}" >&2; exit 1
      }
      [[ "$gpath" == /* ]] && {
        echo "SECURITY: Absolute path rejected — ${gpath}" >&2; exit 1
      }

      if is_denied "$gpath"; then
        ((SKIP_COUNT+=1)) || true
        $DRY_RUN && echo "  SKIP (denylist): ${gpath}"
        continue
      fi

      # Compute destination: strip source prefix, add destination prefix
      local_dst="$mdst/${gpath#$msrc}"
      EXPORT_MAP["$local_dst"]="$gpath"
      ((EXPORT_COUNT+=1)) || true
      $DRY_RUN && echo "  EXPORT (mapped): ${gpath} => ${local_dst}"
    done < <(git -C "$SOURCE" ls-tree -r "$REF" -- "$msrc")
  else
    # Single file mapping — inspect git tree mode
    map_info="$(git -C "$SOURCE" ls-tree "$REF" -- "$msrc" 2>/dev/null)"
    if [[ -z "$map_info" ]]; then
      echo "ERROR: Mapped source file '${msrc}' does not exist at ref ${REF}" >&2
      exit 1
    fi
    map_mode="${map_info%% *}"
    map_otype="${map_info#* }"; map_otype="${map_otype%% *}"

    # Reject symlink (mode 120000)
    [[ "$map_mode" == "120000" ]] && {
      echo "SECURITY: Mapped symlink rejected — ${msrc}" >&2; exit 1
    }
    # Reject submodule (mode 160000, type commit)
    [[ "$map_mode" == "160000" || "$map_otype" == "commit" ]] && {
      echo "SECURITY: Mapped submodule rejected — ${msrc}" >&2; exit 1
    }
    if is_denied "$msrc"; then
      echo "ERROR: Mapped source file '${msrc}' is denied by the denylist" >&2
      exit 1
    fi

    EXPORT_MAP["$mdst"]="$msrc"
    ((EXPORT_COUNT+=1)) || true
    $DRY_RUN && echo "  EXPORT (mapped): ${msrc} => ${mdst}"
  fi
done
fi

echo "Allowlist entries evaluated: ${#ALLOWED_RAW[@]}"
echo "Mapped entries processed  : ${MAP_COUNT}"
echo "Files selected for export : ${EXPORT_COUNT}"
echo "Files excluded by denylist: ${SKIP_COUNT}"
echo ""

# ---- validate individual file entries exist at ref ---------------------
FAILED=0
for entry in "${ALLOWED_RAW[@]}"; do
  # Strip mapping syntax to get the source path
  if [[ "$entry" == *"=>"* ]]; then
    src="$(echo "$entry" | sed -E 's/^[[:space:]]*//; s/[[:space:]]*=>.*//')"
  else
    src="$entry"
  fi
  if [[ "$src" == */ ]]; then
    if [[ -z "$(git -C "$SOURCE" ls-tree -r --name-only "$REF" -- "$src" | head -n 1)" ]]; then
      echo "ERROR: Allowlisted directory '${src}' has no tracked files at ref ${REF}" >&2
      FAILED=$((FAILED + 1))
    fi
    continue
  fi
  if ! git -C "$SOURCE" cat-file -e "${REF}:${src}" 2>/dev/null; then
    echo "ERROR: Allowlisted file '${src}' does not exist at ref ${REF}" >&2
    FAILED=$((FAILED + 1))
  fi
done

[[ $FAILED -gt 0 ]] && {
  echo "ERROR: ${FAILED} allowlist entries are missing from ref ${REF}" >&2
  exit 1
}

# ---- dry-run: show what would happen, zero writes ----------------------
if $DRY_RUN; then
  echo "=== Dry-run complete — no writes to target ==="
  echo "Export summary: ${EXPORT_COUNT} files would be exported, ${SKIP_COUNT} denied"

  # Show what would happen to stale files in target (requires real target)
  if [[ -d "$TARGET" ]] && git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then
    echo ""
    echo "=== Stale target analysis ==="
    STALE=0
    while IFS= read -r tf; do
      [[ -z "$tf" ]] && continue
      [[ "$tf" == .git || "$tf" == .git/* ]] && continue
      if [[ -z "${EXPORT_MAP[$tf]:-}" ]]; then
        echo "  WOULD DELETE: $tf"
        ((STALE+=1)) || true
      fi
    done < <(cd "$TARGET" && git ls-files --cached)
    echo "  ($STALE stale tracked files would be removed)"
  fi

  exit 0
fi

# ---- stage: extract blobs into staging ----------------------------------
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

for dst_path in "${!EXPORT_MAP[@]}"; do
  src_path="${EXPORT_MAP[$dst_path]}"
  dst_abs="${STAGING_DIR}/${dst_path}"
  mkdir -p "$(dirname "$dst_abs")"
  git -C "$SOURCE" show "${REF}:${src_path}" > "$dst_abs"
done

echo "Staged ${#EXPORT_MAP[@]} files in ${STAGING_DIR}"

# ---- reconcile against target -------------------------------------------
echo ""
echo "=== Reconciling target ==="

if [[ ! -d "$TARGET" ]]; then
  mkdir -p "$TARGET"
fi

# rsync: copy staging into target, deleting extra files, but preserve .git
RSYNC_ARGS=(-av --delete --exclude='.git')

if ! rsync "${RSYNC_ARGS[@]}" "${STAGING_DIR}/" "${TARGET}/"; then
  echo "ERROR: rsync failed" >&2
  exit 1
fi

# ---- verify: no untracked/unexpected files remain after reconciliation --
if [[ -d "$TARGET/.git" ]]; then
  echo ""
  echo "=== Verifying target ==="
  while IFS= read -r tf; do
    [[ -z "$tf" ]] && continue
    [[ "$tf" == .git || "$tf" == .git/* ]] && continue

    if [[ -z "${EXPORT_MAP[$tf]:-}" ]]; then
      echo "ERROR: Unexpected file in target after reconciliation: ${tf}" >&2
      exit 1
    fi
  done < <(cd "$TARGET" && find . -not -path './.git/*' -not -path './.git' -type f | sed 's|^\./||')
  echo "Target verification passed."
fi

# ---- done ---------------------------------------------------------------

echo ""
echo "=== Export complete ==="
echo "  Exported: ${EXPORT_COUNT} files"
echo "  Denied  : ${SKIP_COUNT} files"
