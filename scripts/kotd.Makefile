ANSIBLE_EXTRA_ARGS += devconfig_enable_kotd=True
ifeq (y,$(CONFIG_HAVE_DISTRO_CUSTOM_KOTD_REPO))
KOTD_REPO:=$(subst ",,$(CONFIG_CUSTOM_DISTRO_KOTD_REPO))
KOTD_REPO_NAME:=$(subst ",,$(CONFIG_CUSTOM_DISTRO_KOTD_REPO_NAME))
ANSIBLE_EXTRA_ARGS += devconfig_has_kotd_repo=True
ANSIBLE_EXTRA_ARGS += devconfig_kotd_repo=$(KOTD_REPO)
ANSIBLE_EXTRA_ARGS += devconfig_kotd_repo_name=$(KOTD_REPO_NAME)
endif # HAVE_DISTRO_CUSTOM_KOTD_REPO

ANSIBLE_CMD_KOTD_ENABLE :=

kotd: inventory .config
	$(Q)$(ANSIBLE_CMD_KOTD_ENABLE)ansible-playbook $(ANSIBLE_VERBOSE) \
		playbooks/devconfig.yml --tags vars,kotd \
		--extra-vars=@./extra_vars.yaml

kotd-baseline: inventory .config
	$(Q)$(ANSIBLE_CMD_KOTD_ENABLE)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'baseline' \
		playbooks/devconfig.yml \
		--tags vars,kotd \
		--extra-vars=@./extra_vars.yaml

kotd-dev: inventory .config
	$(Q)$(ANSIBLE_CMD_KOTD_ENABLE)ansible-playbook $(ANSIBLE_VERBOSE) \
		--limit 'dev' \
		playbooks/devconfig.yml \
		--tags vars,kotd \
		--extra-vars=@./extra_vars.yaml

kotd-help-menu:
	@echo "kotd options:"
	@echo "kotd                  - Installs the latest kernel"
	@echo "kotd-baseline         - Installs the latest kernel on baseline hosts"
	@echo "kotd-dev              - Installs the latest kernel on dev hosts"
	@echo ""

HELP_TARGETS += kotd-help-menu
