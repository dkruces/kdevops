PHONY += fix-whitespace-last-commit
fix-whitespace-last-commit:
	$(Q)git diff --name-only --diff-filter=M HEAD~1..HEAD | xargs -r python3 scripts/fix_whitespace_issues.py

PHONY += style
style:
	$(Q)if which black > /dev/null ; then black . || true; fi
	$(Q)python3 scripts/detect_whitespace_issues.py || true
	$(Q)python3 scripts/detect_indentation_issues.py || true
	$(Q)python3 scripts/check_commit_format.py || true
	$(Q)python3 scripts/ensure_newlines.py || true

# Per-module lint gates. See docs/module-spec.md.
#
# Usage:
#   make ansible-lint-module MODULE=<name>
#   make python-lint-module  MODULE=<name>
#
# These pass --fix; tree-wide linting stays in `make style` until the
# whole tree is clean enough to enforce globally.

PHONY += ansible-lint-module
ansible-lint-module:
	$(Q)test -n "$(MODULE)" || { echo "Usage: make ansible-lint-module MODULE=<name>"; exit 1; }
	$(Q)ansible-lint --profile=production --fix=all \
		playbooks/$(MODULE).yml \
		playbooks/roles/$(MODULE)/

PHONY += python-lint-module
python-lint-module:
	$(Q)test -n "$(MODULE)" || { echo "Usage: make python-lint-module MODULE=<name>"; exit 1; }
	$(Q)test -d modules/$(MODULE) || { echo "modules/$(MODULE)/ does not exist"; exit 1; }
	$(Q)find modules/$(MODULE) -name '*.py' -print0 | xargs --no-run-if-empty --null black
	$(Q)find modules/$(MODULE) -name '*.py' -print0 | xargs --no-run-if-empty --null ruff check --fix
