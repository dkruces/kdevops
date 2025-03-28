# Kconfig Fragments

kdevops fragments are supported and can be used with the `scripts/kconfig/merge_config.sh` script.

Workflow:

```sh
./scripts/kconfig/merge_config.sh \
-m <INITCONF> \
<FRAGMENT_LIST>
```

Example:

```sh
./scripts/kconfig/merge_config.sh \
-m .config \
callback-dense.config
```
