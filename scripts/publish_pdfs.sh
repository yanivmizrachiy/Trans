#!/usr/bin/env bash
# Publish freshly built PDFs, rendered HTML and preview sheets to the
# publication branch, but only while the sources they were built from are
# still the current ones on that branch.
#
# Called by .github/workflows/build-pdfs.yml after every build step passed.
# Tested by scripts/test_publish_pdfs.py against a throwaway Git remote.
#
# Environment:
#   PUBLISH_REMOTE   remote name            (default: origin)
#   PUBLISH_BRANCH   publication branch     (default: main)
#   PUBLISH_BASE     commit the build ran on (default: HEAD)
#   PUBLISH_ATTEMPTS push retries           (default: 3)
#   PUBLISH_CONFIRM  must be "1": the script hard-resets the working tree to
#                    the remote branch, so it is only for CI checkouts and tests.
set -euo pipefail

REMOTE="${PUBLISH_REMOTE:-origin}"
BRANCH="${PUBLISH_BRANCH:-main}"
BASE="${PUBLISH_BASE:-$(git rev-parse HEAD)}"
ATTEMPTS="${PUBLISH_ATTEMPTS:-3}"

if [ "${PUBLISH_CONFIRM:-}" != "1" ]; then
  echo "Refusing to run: publish_pdfs.sh resets the working tree to $REMOTE/$BRANCH. Set PUBLISH_CONFIRM=1 in CI or tests." >&2
  exit 2
fi

# Everything that feeds the PDF build. A newer commit touching any of these
# makes this build stale; it must then publish nothing.
SOURCES=(
  worksheets/ assets/ scripts/build_pdfs.py
  book/teacher.html scripts/build_teacher.py
  book/official.html sources/ministry/ scripts/build_official.py
  book/front.html book/sadna.html book/krispin-video.html scripts/build_complete.py scripts/visual_audit.py
  docs/ANSWER_KEY.md docs/TEACHER_WORKSHOP.md
)
# Everything the build produces. Directories are copied whole, so a worksheet
# or preview sheet that did not exist before the build is published too.
OUTPUT_DIRS=(pdf qa/previews)
OUTPUT_FILES=(
  book/teacher.pdf book/official.pdf book/front.pdf book/workshop.pdf
  book/sadna.pdf book/krispin-video.pdf book/answers.pdf book/transformations-complete.pdf
  book/workshop.html book/answers.html
)

if [ -z "$(git config user.name)" ]; then
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
fi

# Stash every build output outside the working tree *before* touching Git.
# After "git reset --hard" below, a file that an earlier (rejected) attempt had
# committed would otherwise disappear from the tree together with its commit.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
for dir in "${OUTPUT_DIRS[@]}"; do
  mkdir -p "$STAGE/$dir"
  cp -R "$dir"/. "$STAGE/$dir/"
done
for file in "${OUTPUT_FILES[@]}"; do
  mkdir -p "$STAGE/$(dirname "$file")"
  cp "$file" "$STAGE/$file"
done
built_pdfs=$(find "$STAGE/pdf" -name '*.pdf' | wc -l)
if [ "$built_pdfs" -lt 1 ]; then
  echo "No worksheet PDFs were built; refusing to publish an empty set." >&2
  exit 1
fi
echo "Staged $built_pdfs worksheet PDFs, ${#OUTPUT_FILES[@]} booklet files and $(find "$STAGE/qa/previews" -type f | wc -l) preview sheets built from $BASE"

for attempt in $(seq 1 "$ATTEMPTS"); do
  git fetch "$REMOTE" "$BRANCH"
  if ! git diff --quiet "$BASE" "$REMOTE/$BRANCH" -- "${SOURCES[@]}"; then
    echo "A newer commit on $BRANCH changed PDF source files. This build is superseded; publishing nothing."
    exit 0
  fi
  if ! git diff --quiet "$BASE" "$REMOTE/$BRANCH" -- "${OUTPUT_DIRS[@]}" "${OUTPUT_FILES[@]}"; then
    echo "Another run has already published outputs for this source revision. Avoiding binary conflicts."
    exit 0
  fi
  git reset --hard "$REMOTE/$BRANCH"
  # Restore every staged output. Files that are tracked on the branch but were
  # not rebuilt (for example a renamed worksheet's old PDF) are left in place,
  # so published URLs never disappear through this script.
  for dir in "${OUTPUT_DIRS[@]}"; do
    mkdir -p "$dir"
    cp -R "$STAGE/$dir"/. "$dir/"
  done
  for file in "${OUTPUT_FILES[@]}"; do
    cp "$STAGE/$file" "$file"
  done
  git add -- "${OUTPUT_DIRS[@]}" "${OUTPUT_FILES[@]}"
  if git diff --cached --quiet; then
    echo "All published outputs already match the generated files."
    exit 0
  fi
  git diff --cached --stat
  git commit -q -m "Generate verified transformation PDFs [skip ci]"
  if git push "$REMOTE" HEAD:"$BRANCH"; then
    echo "Verified PDF publication succeeded (attempt $attempt)."
    exit 0
  fi
  echo "Branch advanced concurrently; retrying on fresh $BRANCH (attempt $attempt of $ATTEMPTS)."
done
echo "PDF publication could not safely advance $BRANCH after $ATTEMPTS attempts." >&2
exit 1
