# SPDX-License-Identifier: copyleft-next-0.3.1

monitoring-results: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/monitor-results.yml \
		--extra-vars=@./extra_vars.yaml)
PHONY += monitoring-results

monitoring-cleanup: $(KDEVOPS_EXTRA_VARS)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/monitor-kill.yml \
		--extra-vars=@./extra_vars.yaml)
PHONY += monitoring-cleanup

monitoring-help-menu:
	@echo "monitoring options:"
	@echo "monitoring-results                       - Collect interim monitoring data without stopping monitors"
	@echo "monitoring-cleanup                       - Kill running monitors and remove collected data"
	@echo ""

HELP_TARGETS += monitoring-help-menu
