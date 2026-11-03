#!/usr/bin/env python3
"""Behavioural regression test for the PDF publication step of build-pdfs.yml.

The publication logic lives in scripts/publish_pdfs.sh. This test does not
inspect the shell text; it runs the script against a throwaway Git remote
(a bare repository standing in for GitHub) and checks what actually lands on
the publication branch:

1. a worksheet PDF that did not exist before the build is published;
2. a source commit that lands after the build supersedes it (nothing is pushed);
3. an unrelated commit that lands after the build is kept and the PDFs are
   published on top of it;
4. outputs already published by another run are not published twice;
5. previously published PDFs are never deleted, even when a worksheet is
   renamed (public URLs stay valid);
6. a rejected push is retried on the fresh branch tip.

Usage: python scripts/test_publish_pdfs.py [path/to/publish-script]
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "scripts" / "publish_pdfs.sh"
BOOK_PDFS = ("teacher", "official", "workshop", "sadna", "krispin-video", "answers", "transformations-complete")
ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "publish-test", "GIT_AUTHOR_EMAIL": "publish-test@example.invalid",
    "GIT_COMMITTER_NAME": "publish-test", "GIT_COMMITTER_EMAIL": "publish-test@example.invalid",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull,
    "PUBLISH_CONFIRM": "1",
}


def git(cwd, *args, check=True):
    return subprocess.run(["git", *args], cwd=cwd, env=ENV, check=check,
                          capture_output=True, text=True, encoding="utf-8")


def write(repo, relative, content):
    path = Path(repo) / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)


def seed_repository(root):
    """Create bare 'origin' plus a working clone with the tracked layout used by the real repo."""
    origin = root / "origin.git"
    git(root, "init", "--bare", "--initial-branch=main", str(origin))
    work = root / "work"
    git(root, "clone", "--quiet", str(origin), str(work))
    git(work, "config", "user.name", "publish-test")
    git(work, "config", "user.email", "publish-test@example.invalid")
    write(work, "worksheets/a.html", "<html>a</html>")
    write(work, "pdf/a.pdf", "%PDF-a-v1")
    for name in BOOK_PDFS:
        write(work, f"book/{name}.pdf", f"%PDF-{name}-v1")
    write(work, "book/workshop.html", "<p>workshop v1</p>")
    write(work, "book/answers.html", "<p>answers v1</p>")
    write(work, "qa/previews/sheet.jpg", "jpg-v1")
    write(work, "docs/ANSWER_KEY.md", "# key v1")
    write(work, "README.md", "readme v1")
    git(work, "add", "-A")
    git(work, "commit", "-q", "-m", "seed")
    git(work, "push", "-q", "origin", "HEAD:main")
    return origin, work


def clone(root, origin, name):
    other = root / name
    git(root, "clone", "--quiet", str(origin), str(other))
    git(other, "config", "user.name", "publish-test")
    git(other, "config", "user.email", "publish-test@example.invalid")
    return other


def commit_and_push(repo, relative, content, message):
    write(repo, relative, content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message)
    git(repo, "push", "-q", "origin", "HEAD:main")


def simulate_build(work, version, worksheet_ids):
    """Pretend scripts/build_*.py ran: every output is rewritten, new worksheets gain a PDF."""
    for ident in worksheet_ids:
        write(work, f"pdf/{ident}.pdf", f"%PDF-{ident}-{version}")
    for name in BOOK_PDFS:
        write(work, f"book/{name}.pdf", f"%PDF-{name}-{version}")
    write(work, "book/workshop.html", f"<p>workshop {version}</p>")
    write(work, "book/answers.html", f"<p>answers {version}</p>")
    write(work, "qa/previews/sheet.jpg", f"jpg-{version}")


def publish(work):
    return subprocess.run([bash_executable(), str(SCRIPT)], cwd=work, env=ENV,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def tree(origin):
    return set(git(origin, "ls-tree", "-r", "--name-only", "main").stdout.split())


def blob(origin, relative):
    shown = git(origin, "show", f"main:{relative}", check=False)
    return shown.stdout if shown.returncode == 0 else None


def log(origin):
    return git(origin, "log", "--format=%s", "main").stdout.splitlines()


def expect(condition, message, result=None):
    if not condition:
        detail = "" if result is None else f"\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        raise AssertionError(message + detail)


CASES = []


def scenario(func):
    CASES.append(func)
    return func


def bash_executable():
    """Git for Windows ships bash next to git; the System32 bash.exe is WSL and unusable here."""
    override = os.environ.get("PUBLISH_BASH")
    if override:
        return override
    git_path = shutil.which("git")
    if git_path and os.name == "nt":
        install = Path(git_path).resolve().parent.parent
        for candidate in (install / "bin" / "bash.exe", install / "usr" / "bin" / "bash.exe"):
            if candidate.is_file():
                return str(candidate)
    return shutil.which("bash") or "bash"


@scenario
def new_worksheet_pdf_is_published(root):
    origin, work = seed_repository(root)
    commit_and_push(work, "worksheets/new.html", "<html>new</html>", "add new worksheet")
    simulate_build(work, "v2", ["a", "new"])
    result = publish(work)
    expect(result.returncode == 0, "publish must succeed", result)
    expect("pdf/new.pdf" in tree(origin), "new worksheet PDF missing from publication branch", result)
    expect(blob(origin, "pdf/new.pdf") == "%PDF-new-v2", "new PDF has wrong bytes", result)
    expect(blob(origin, "pdf/a.pdf") == "%PDF-a-v2", "existing PDF was not refreshed", result)
    expect(blob(origin, "book/transformations-complete.pdf") == "%PDF-transformations-complete-v2",
           "complete booklet was not refreshed", result)
    expect(blob(origin, "book/workshop.html") == "<p>workshop v2</p>", "rendered HTML was not refreshed", result)
    expect(blob(origin, "qa/previews/sheet.jpg") == "jpg-v2", "preview sheet was not refreshed", result)
    expect(log(origin)[0].startswith("Generate verified transformation PDFs"), "unexpected publish commit", result)


@scenario
def superseded_source_change_publishes_nothing(root):
    origin, work = seed_repository(root)
    commit_and_push(work, "worksheets/new.html", "<html>new</html>", "add new worksheet")
    simulate_build(work, "v2", ["a", "new"])
    other = clone(root, origin, "other")
    commit_and_push(other, "worksheets/a.html", "<html>a changed after build</html>", "later source edit")
    result = publish(work)
    expect(result.returncode == 0, "a superseded build must exit cleanly", result)
    expect("pdf/new.pdf" not in tree(origin), "stale build must not publish outputs", result)
    expect(blob(origin, "pdf/a.pdf") == "%PDF-a-v1", "stale build overwrote a PDF", result)
    expect(log(origin)[0] == "later source edit", "stale build created a commit", result)


@scenario
def unrelated_concurrent_commit_is_preserved(root):
    origin, work = seed_repository(root)
    commit_and_push(work, "worksheets/new.html", "<html>new</html>", "add new worksheet")
    simulate_build(work, "v2", ["a", "new"])
    other = clone(root, origin, "other")
    commit_and_push(other, "README.md", "readme v2 (docs only)", "docs edit during build")
    result = publish(work)
    expect(result.returncode == 0, "publish after an unrelated commit must succeed", result)
    expect(blob(origin, "README.md") == "readme v2 (docs only)", "concurrent docs commit was lost", result)
    expect(blob(origin, "pdf/new.pdf") == "%PDF-new-v2", "new PDF missing after unrelated commit", result)
    expect(log(origin)[1] == "docs edit during build", "publish commit must sit on top of the concurrent commit", result)


@scenario
def already_published_outputs_skip(root):
    origin, work = seed_repository(root)
    commit_and_push(work, "worksheets/new.html", "<html>new</html>", "add new worksheet")
    simulate_build(work, "v2", ["a", "new"])
    other = clone(root, origin, "other")
    simulate_build(other, "v2", ["a", "new"])
    git(other, "add", "-A")
    git(other, "commit", "-q", "-m", "Generate verified transformation PDFs [skip ci] (other run)")
    git(other, "push", "-q", "origin", "HEAD:main")
    result = publish(work)
    expect(result.returncode == 0, "duplicate run must exit cleanly", result)
    expect(len(log(origin)) == 3, "duplicate run must not add a second publish commit", result)


@scenario
def renamed_worksheet_keeps_old_public_pdf(root):
    origin, work = seed_repository(root)
    git(work, "mv", "worksheets/a.html", "worksheets/b.html")
    git(work, "commit", "-q", "-m", "rename worksheet")
    git(work, "push", "-q", "origin", "HEAD:main")
    simulate_build(work, "v2", ["b"])  # the build only produces b.pdf; a.pdf is still tracked
    result = publish(work)
    expect(result.returncode == 0, "publish after rename must succeed", result)
    published = tree(origin)
    expect("pdf/a.pdf" in published, "publication must never delete an existing public PDF", result)
    expect("pdf/b.pdf" in published, "renamed worksheet PDF missing", result)


@scenario
def rejected_push_is_retried(root):
    origin, work = seed_repository(root)
    commit_and_push(work, "worksheets/new.html", "<html>new</html>", "add new worksheet")
    simulate_build(work, "v2", ["a", "new"])
    hook = origin / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nif [ ! -f \"$GIT_DIR/first-push-rejected\" ]; then\n"
                    "  touch \"$GIT_DIR/first-push-rejected\"\n  echo 'simulated concurrent update' >&2\n  exit 1\nfi\nexit 0\n",
                    encoding="utf-8", newline="\n")
    hook.chmod(0o755)
    result = publish(work)
    expect(result.returncode == 0, "publish must retry after a rejected push", result)
    expect((origin / "first-push-rejected").exists(), "hook did not run", result)
    expect(blob(origin, "pdf/new.pdf") == "%PDF-new-v2", "retry did not publish the new PDF", result)
    expect(len(log(origin)) == 3, "retry must produce exactly one publish commit", result)


def main():
    if not SCRIPT.is_file():
        raise SystemExit(f"Publish script not found: {SCRIPT}")
    failures = []
    for case in CASES:
        root = Path(tempfile.mkdtemp(prefix="trans-publish-"))
        try:
            case(root)
            print(f"PASS {case.__name__}")
        except AssertionError as exc:
            failures.append(case.__name__)
            print(f"FAIL {case.__name__}: {exc}")
        finally:
            shutil.rmtree(root, ignore_errors=True)
    if failures:
        raise SystemExit(f"FAIL: {len(failures)} of {len(CASES)} publication scenarios failed: {failures}")
    print(f"PASS: {len(CASES)} publication scenarios against {SCRIPT.name}")


if __name__ == "__main__":
    main()
