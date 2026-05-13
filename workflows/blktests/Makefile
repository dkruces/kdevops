# SPDX-License-Identifier: copyleft-next-0.3.1

export KDEVOPS_BLKTESTS_CONFIG :=
export KDEVOPS_BLKTESTS_CONFIG_TEMPLATE :=

KDEVOPS_BLKTESTS_SCRIPTS_PATH=workflows/blktests/scripts

BLKTESTS_DYNAMIC_RUNTIME_VARS := "kdevops_run_blktests": True
ifneq (,$(RUN_FAILURES))
BLKTESTS_DYNAMIC_RUNTIME_VARS += $(comma) "run_tests_on_failures": True
endif

ifneq (,$(SKIP_RUN))
BLKTESTS_DYNAMIC_RUNTIME_VARS += $(comma) "blktests_skip_run": True
endif

blktests: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		playbooks/blktests.yml \
		--skip-tags run_tests$(comma)copy_results $(LIMIT_HOSTS))

blktests-baseline: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		--limit baseline \
		playbooks/blktests.yml \
		--tags vars$(comma)run_tests$(comma)copy_results \
		--extra-vars '{ $(BLKTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS))

blktests-baseline-skip-kdevops-update: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		--limit baseline \
		playbooks/blktests.yml \
		--tags vars$(comma)run_tests$(comma)copy_results --skip-tags git_update \
		--extra-vars '{ $(BLKTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS))

blktests-baseline-run-oscheck-only: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		--limit baseline \
		playbooks/blktests.yml \
		--tags vars$(comma)run_tests$(comma)copy_results \
		--skip-tags git_update$(comma)reboot$(comma)clean_results \
		--extra-vars '{ $(BLKTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS))

blktests-dev: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		--limit dev \
		playbooks/blktests.yml \
		--tags vars$(comma)run_tests$(comma)copy_results \
		--extra-vars '{ $(BLKTESTS_DYNAMIC_RUNTIME_VARS) }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS))

blktests-baseline-results: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		--limit baseline \
		playbooks/blktests.yml \
		--tags copy_results$(comma)print_results \
		--extra-vars '{ kdevops_run_blktests: True }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS))

blktests-results: blktests-baseline-results

blktests-dev-results: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		--limit dev \
		playbooks/blktests.yml \
		--tags copy_results$(comma)print_results \
		--extra-vars '{ kdevops_run_blktests: True }' \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS))

blktests-help-menu:
	@echo "blktests options:"
	@echo "blktests                                 - Git clones blktests, builds and install it"
	@echo "blktests-baseline                        - Run blktests on baseline hosts and collect results"
	@echo "blktests-dev                             - Run blktests on dev hosts and collect results"
	@echo "blktests-baseline-results                - Only collect results for baseline hosts"
	@echo "blktests-dev-results                     - Only collect results for dev hosts"
	@echo "blktests-baseline-skip-kdevops-update    - Run blktests but skip updating kdevops"
	@echo "blktests-baseline-run-oscheck-only       - Only run oscheck"
	@echo ""

HELP_TARGETS += blktests-help-menu
