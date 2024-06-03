# SPDX-License-Identifier: copyleft-next-0.3.1

include scripts/gen-kreleases.Makefile
include scripts/gen-gitref.Makefile

PHONY += refs-help-menu
refs-help-menu:
	@echo "Generate git references options"
	@echo "gen-kreleases   - Generate latest-and-greatest and statically"
	@echo "                  defined git references (trees: linus, next and stable)"
	@echo "gen-gitref      - Generate last 15 git references available"
	@echo "gen-gitref-0    - Generate static git references only"
	@echo "clean-gitref    - Remove git references all files"
	@echo ""

HELP_TARGETS += refs-help-menu
.PHONY = $(PHONY)
