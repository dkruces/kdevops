# kdevops module specification

A **module** is a self-contained, user-selectable unit. Every module
has the same canonical layout.

## Module layout

```
modules/<name>/
├── Kconfig             user-facing options
├── Makefile            user-facing targets
├── README.md           contributor reference
├── scripts/            module-owned helper scripts (optional)
├── <submodule>/        zero or more sub-modules (optional)
│   └── ...
└── ...                 module-owned assets (configs, templates, data)
playbooks/<name>.yml    Ansible entry point         (optional)
playbooks/roles/<name>/ Ansible role implementing the work (optional)
```

`<name>` is the same string everywhere.

A module MUST have a Kconfig, Makefile, and README. The playbook
and role are optional: a **config-only module** declares
configuration that other modules consume but owns no playbook or
role of its own. Example: `libvirt` declares the libvirt provider's
configuration (libvirt_*, qemu_*) which the `guestfs` role consumes;
libvirt has no top-level playbook or role of its own.
The README MUST state explicitly when a module is config-only and
which other module's role uses its configuration.

## Naming

`<name>` is lowercase `snake_case`. No dashes. No leading or trailing
underscore. Identical across the Kconfig path, Makefile path, README
directory, playbook filename, and role directory.

Make targets use `-` separators; role names use `_` separators.

## Sub-modules

A **sub-module** is a separately-configurable unit nested under its
parent. The parent triggers it via tags on its single orchestrator
playbook (see below) or via dedicated Make targets.

```
modules/<name>/<sub>/
├── Kconfig             optional (only if it has user options)
├── Makefile            optional (only if it registers Make targets)
├── README.md           required
├── scripts/            sub-module-owned helper scripts (optional)
└── ...                 sub-module-owned assets
playbooks/roles/<name>/<sub>/       physically nested sub-role
├── tasks/main.yml
├── defaults/main.yml                role-private only
└── ...
```

The sub-module's Kconfig is sourced from the parent:

```
# modules/<name>/Kconfig
source modules/<name>/<sub>/Kconfig
```

The sub-role lives **physically nested under the parent role's
directory** (not as a flat `<name>_<sub>` sibling). The parent's
`tasks/main.yml` references it by the slash-separated path
`<name>/<sub>`:

```yaml
# playbooks/roles/<name>/tasks/main.yml
- name: Run the <sub> sub-role
  ansible.builtin.include_role:
    name: <name>/<sub>    # resolves to playbooks/roles/<name>/<sub>/
  tags: [<sub>]
```

Ansible's role-path resolver at
`ansible/lib/ansible/playbook/role/definition.py:186` walks each
configured `roles_path` entry and joins the role name via
`os.path.join(path, role_name)`. A role name that contains a `/` is
treated as a subdirectory under each search path, so
`roles_path=playbooks/roles` + `name=<name>/<sub>` resolves to
`playbooks/roles/<name>/<sub>/`. Runtime `include_role` does not
propagate the parent role's directory as a search base (only
`meta/main.yml` dependencies do, via
`ansible/lib/ansible/playbook/role/metadata.py:88`), so the explicit
slash form is the canonical way to reach a nested sub-role.

Reach for a sub-module when a piece of work:
- has user options worth surfacing in `menuconfig`,
- has Make targets distinct from the parent's,
- has its own assets,
- or wraps controller-side sudo (see "Controller-side sudo isolation").

### One playbook per module

A module has **one** Ansible entry-point playbook at
`playbooks/<name>.yml`. There is no `playbooks/<name>_<sub>.yml` per
sub-module — instead the orchestrator playbook runs the parent role,
which conditionally includes the appropriate sub-role(s) based on
tags supplied by the invoking Make target. The Make target is the
single switch:

```
<name>-<sub>-setup: $(KDEVOPS_EXTRA_VARS)
        $(call run-ansible-playbook, \
                $(KDEVOPS_PLAYBOOKS_DIR)/<name>.yml \
                --tags <sub>_setup \
                --extra-vars=@./extra_vars.yaml)
```

This keeps the playbook count proportional to module count, not
module × sub-module count.

### Sub-sub-modules

Sub-modules nest recursively. A sub-module can itself host
sub-modules at any depth:

```
modules/<name>/<sub>/<subsub>/
├── Kconfig
├── Makefile
└── README.md
playbooks/roles/<name>/<sub>/<subsub>/
├── tasks/main.yml
└── ...
```

The same slash-in-name resolution cascades: the `<sub>` role's
`tasks/main.yml` invokes `include_role: { name: <name>/<sub>/<subsub> }`
and Ansible resolves it to `playbooks/roles/<name>/<sub>/<subsub>/`.
A common use is splitting one sub-module into a non-sudo `verify/`
sub-sub-module and an opt-in sudo `setup/` sub-sub-module — see
"Controller-side sudo isolation" below.

### Sub-roles (NOT sub-modules)

A **sub-role** is internal role organization — a helper invoked via
`include_role` / `import_role` from the parent module's role. It has
no Kconfig, no Makefile, no user-facing targets. It exists to keep
the parent role's task files lean. Sub-roles live nested under the
parent role just like sub-modules:

```
playbooks/roles/<name>/<helper>/    role only, no module dir
```

Examples: `<name>/prep_localhost`, `<name>/collect_results`. They are
referenced from the parent role with the same slash-separated form
(`include_role: name: <name>/<helper>`) and resolved by ansible-core's
role-path resolver as described above.

## Controller-side sudo isolation

Tasks that run on the controller (`hosts: localhost`,
`delegate_to: localhost`, `connection: local`) and require `become: true`
MUST be isolated in a dedicated sub-module (or sub-sub-module) and
**MUST NOT** be included by the parent role's default execution
path. This rule applies only to controller-side sudo — guest-side
`become: true` (`hosts: all` or specific target hosts) is unrestricted.

Rationale: kdevops is a contributor's tool. The developer's host is
not a production target; running unsolicited sudo on it during a
plain `make` or `make bringup` invocation is an abuse of trust. The
opt-in Make target makes every sudo step explicit.

### Verify-then-diagnose

The parent role's default execution path MUST include a non-sudo
`verify` sub-role that inspects whether the state the sudo sub-module
would create is already present. The verify path:

- runs without `become:` (pure-read: `stat`, `getent`, `command:
  getfacl`, ansible facts, etc.),
- succeeds silently when the host is already in the desired state,
- fails via `ansible.builtin.fail` with a structured diagnostic
  message when it isn't, naming both the opt-in Make target and the
  documentation file the user can follow to do it manually.

```yaml
# playbooks/roles/<name>/<sub>/verify/tasks/main.yml
- name: Verify <sub> host state
  ansible.builtin.stat:
    path: /path/to/expected
  register: <name>_<sub>_state

- name: Fail with actionable diagnostic
  ansible.builtin.fail:
    msg: |
      <sub> setup is incomplete: <what is missing>.

      Two ways to fix this:
        1. Run the opt-in sudo target:
               make <name>-<sub>-setup
        2. Follow the manual setup in docs/<name>-<sub>.md, then
           re-run the original make target.
  when: not <name>_<sub>_state.stat.exists
```

The opt-in sudo work lives in a sibling `setup/` sub-sub-module
that the verify path's parent role conditionally includes via tag.
Tags are invoked exclusively through the dedicated Make target;
they are not part of the default execution.

The module's `docs/<name>.md` MUST document the sudo target AND the
manual sequence. A user who refuses to grant the controller sudo
must always have a complete, scripted-or-manual alternative.

## Module assets

Where to place the module's own files:

| Kind | Location | Notes |
|---|---|---|
| Controller-side helper scripts (invoked by Make) | `modules/<name>/scripts/` | Module-owned. Not searched by Ansible. |
| Files Ansible deploys to guests | `playbooks/roles/<name>/files/` | Ansible canonical. |
| Jinja2 templates Ansible renders | `playbooks/roles/<name>/templates/` | Ansible canonical. |
| Module-owned configs, data, fixtures | `modules/<name>/<topic>/` | Free-form. Examples: `configs/`, `expunges/`, `osfiles/`. |

## Module vocabulary

kdevops owns a small uniform vocabulary that names what each piece
of a module does. The vocabulary is small on purpose: a user who
learns the meaning of `build_deps`, `runtime_deps`, `do_compile`,
or `do_deploy` in one module knows what those names mean in every
other module. The Make-target spelling, the sub-module directory
names, and the per-task tags all draw from the same word list.

The vocabulary is borrowed from the Yocto Project's recipe model
where the semantics translate cleanly. Yocto's
[tasks reference](https://docs.yoctoproject.org/ref-manual/tasks.html)
and [variables reference](https://docs.yoctoproject.org/ref-manual/variables.html)
are the authoritative source for the underlying ideas; this section
records the kdevops-specific interpretation, the kdevops-owned
extensions where Yocto has no equivalent, and the spelling
conventions that follow from both. Once a term is documented here,
it is the canonical spelling for that concept across the kdevops
tree — modules, sub-modules, Makefile targets, role directories,
Ansible tags, and docs.

### Dependency vocabulary

kdevops adopts Yocto's build-time vs runtime dependency split for
naming **sub-modules** that perform host-side dependency
installation:

| Sub-module name | Yocto analog | Kdevops meaning |
|---|---|---|
| `<module>/build_deps/` | `DEPENDS` | Install build-time tools the module's compile step needs (compiler, meson, ninja, -dev/-devel headers). Used when the module compiles something. |
| `<module>/runtime_deps/` | `RDEPENDS` | Install runtime tools the module needs to operate after build (e.g. `libguestfs-tools` so the `virt-builder` binary is on PATH). Used when the module orchestrates external workloads. |

Both spellings are intentional snake_case to match the rest of the
sub-module naming. The Make-target convention is mechanical:

```
make <module>-build-deps-setup     install build-time tools (sudo)
make <module>-runtime-deps-setup   install runtime tools (sudo)
```

A user reading `make qemu-build-deps-setup` knows from the
spelling alone that it installs build-time tooling, without
opening the README.

Yocto's `RRECOMMENDS`, `RSUGGESTS`, `RPROVIDES`, `RREPLACES`, and
`RCONFLICTS` have no kdevops counterpart today. They are reserved
in this taxonomy for future use; do not invent alternative
spellings for those concepts.

### Host-configuration vocabulary

Yocto recipes do not configure the developer's host system; their
target is the cross-compiled image. kdevops does need host
configuration (group membership, sysfs permissions, libvirt pool
directories, default networks). Those sub-modules live under
domain-specific names rather than a generic `host_config`
umbrella because the domain (`user`, `storage_pool`, `network`,
`pcie_passthrough`, ...) is what users search for:

| Sub-module name | Meaning |
|---|---|
| `<module>/user/` | Controller user / group membership setup |
| `<module>/storage_pool/` | Storage pool directory creation, ownership, and libvirt registration |
| `<module>/network/` | Network plumbing on the controller (dnsmasq, libvirt default network, …) |
| `<module>/pcie_passthrough/` | PCIe device passthrough preparation |

These are kdevops-owned spellings (no Yocto counterpart). The Make
target follows the same shape:

```
make <module>-<feature>-setup     opt-in host configuration for <feature>
```

### Task vocabulary (do_*)

Ansible tags on individual tasks classify what each task does.
The vocabulary maps to Yocto's
[recipe tasks](https://docs.yoctoproject.org/ref-manual/tasks.html)
where the meaning translates without distortion; the kdevops
column is the binding interpretation for this tree.

| Tag | Yocto reference | Kdevops meaning |
|---|---|---|
| `do_fetch` | [`do_fetch`](https://docs.yoctoproject.org/ref-manual/tasks.html#do-fetch) | Acquire sources: `git clone`, meson subprojects download, tarball fetch, mkdir of fetch destination directories. |
| `do_configure` | [`do_configure`](https://docs.yoctoproject.org/ref-manual/tasks.html#do-configure) | Configure the source for the build: `meson configure`, `./configure`, kernel-config selection. **Restricted to build-time configuration of the recipe's own source.** Host configuration (chown, group add, sysfs perms, rendering an ansible.cfg) is NOT `do_configure`. |
| `do_compile` | [`do_compile`](https://docs.yoctoproject.org/ref-manual/tasks.html#do-compile) | Compile the source: `ninja`, `make`, `cargo build`. |
| `do_install` | [`do_install`](https://docs.yoctoproject.org/ref-manual/tasks.html#do-install) | Install the recipe's own built artifacts into a holding area, OR install image-level content (cp a base image into a per-VM holding directory, `virt-sysprep` customisation of an image, `qemu-img create` of an extra drive). Distro package install (apt/dnf/zypper) is also `do_install`; Yocto treats those as `DEPENDS` / `RDEPENDS` resolution rather than a task, but the package-manager invocation is install-shaped and the tag carries the right meaning for kdevops users. |
| `do_deploy` | [`do_deploy`](https://docs.yoctoproject.org/ref-manual/tasks.html#do-deploy) | Write final output to its deployment location. For kdevops this is: `systemctl enable/start` of a service, `virsh net-start`, `virsh define` + `virsh start` of a VM, dropping a udev rule into `/etc/udev/rules.d/`, attaching a PCIe device. |
| `do_clean` | [`do_clean`](https://docs.yoctoproject.org/ref-manual/tasks.html#do-clean) | Remove output. For kdevops: `virsh destroy` + `virsh undefine` + storage volume cleanup, removing stale ownership on a generated file. Yocto's `do_clean` is the precedent; kdevops does not yet implement `do_cleanall` or `do_cleansstate`. |

Tasks that are NOT operations in the do_* sense stay untagged.
That includes:

- pre-flight state probes (`stat`, `getent`, `command -v` lookups,
  `set_fact` of derived paths) — these read state, they do not
  change it.
- The verify sub-sub-modules created under
  [Controller-side sudo isolation](#controller-side-sudo-isolation)
  — every task in `<sub>/verify/` is a probe.
- `include_tasks` / `import_tasks` dispatchers that pull in a
  distro-specific implementation — the do_* tag belongs on the
  leaf task, not the dispatcher.

### Tasks kdevops does NOT borrow from Yocto

The following Yocto tasks are deliberately not in kdevops's
vocabulary, to keep the list short and the semantics tight:

| Yocto task | Why kdevops does not borrow it |
|---|---|
| `do_build` | Yocto reserves this for the meta-task that depends on every other task. Reusing the name for "compile" causes precisely the confusion the vocabulary is meant to prevent. Use `do_compile`. |
| `do_unpack` | kdevops does not unpack tarballs as a separate step; tarballs that need extraction get extracted as part of `do_fetch`. |
| `do_patch` | kdevops modules do not patch source. If a module ever needs to, this term is reserved. |
| `do_package`, `do_package_*` | kdevops does not produce distribution packages. |
| `do_populate_sysroot`, `do_populate_lic`, `do_populate_sdk` | kdevops is not a cross-build system. |
| `do_rootfs`, `do_image`, `do_image_complete`, `do_bootimg` | Yocto's image-recipe machinery does not apply; kdevops's VM provisioning lands artifacts via `do_install` (cp + sysprep) + `do_deploy` (virsh define+start). |

If a kdevops module ever has a genuine match for one of those
tasks, this section is the place to add it back with the kdevops
interpretation pinned. Inventing a new `do_*` name outside of
this list is a spec violation — propose it here first.

### Make-target taxonomy

The vocabulary above pins the spelling of every public Make
target. The shape is:

```
make <module>                       default work for the module
make <module>-<sub>-setup           opt-in sudo sub-module setup
make <module>-<sub>-<op>            sub-module-scoped operation
make <module>-cleanup               opt-in cleanup operation
make <module>-<op>                  module-scoped operation
```

Concrete examples that follow the convention:

| Target | Sub-module | Tag selection |
|---|---|---|
| `make qemu-build-deps-setup` | `qemu/build_deps/` | `--tags qemu_build_deps_setup` |
| `make guestfs-runtime-deps-setup` | `guestfs/runtime_deps/` | `--tags guestfs_runtime_deps_setup` |
| `make libvirt-user-setup` | `libvirt/user/` | `--tags libvirt_user_setup` |
| `make libvirt-storage-pool-setup` | `libvirt/storage_pool/` | `--tags libvirt_storage_pool_setup` |
| `make libvirt-pcie-passthrough-setup` | `libvirt/pcie_passthrough/` | `--tags libvirt_pcie_passthrough_setup` |
| `make guestfs-network-setup` | `guestfs/network/` | `--tags guestfs_network_setup` |
| `make ansible-inventory-cleanup` | `ansible_inventory/cleanup/` | `--tags cleanup_setup` |

Make targets that wrap `ansible-playbook` always use the
`run-ansible-playbook` macro and pass exactly one of the
`--tags` selections above.

### Tag axes for ansible-playbook

A user invoking `ansible-playbook` directly (rather than through
Make) selects work along three orthogonal axes:

| Axis | Tag form | Selects |
|---|---|---|
| 1. Sub-module gate | `<module>_<sub>_setup` (also `_cleanup`) | All work inside one sub-module's opt-in sudo path |
| 2. Operation kind | `do_<verb>` from the table above | All tasks of one operation kind, across whatever sub-modules are already in scope |
| 3. Artifact / area | module-defined (e.g. `hosts`, `nodes`, `vars`) | Module-local filter, not standardised |

The parent role's orchestrator wires the sudo opt-in via
`tags: [never, <module>_<sub>_setup]` on the `include_role` and
`apply: tags: [<module>_<sub>_setup]` inside it, so a single
`--tags <module>_<sub>_setup` selects every task inside that
sub-module's setup path.

`--tags do_compile` on its own does **not** bypass a sudo gate:
the parent's `[never, <gate>]` wrapper still blocks the include
unless `<gate>` is also matched. The composed form
`--tags <gate>,do_compile` is the canonical way to run one
operation kind inside one sub-module. Sudo isolation outranks
operation-kind selection by design.

### Vocabulary discipline

Three rules keep the vocabulary stable:

1. **Sub-module spellings come from this section.** New
   sub-modules pick a name from the dependency vocabulary
   (`build_deps`, `runtime_deps`) or the host-configuration
   vocabulary (`user`, `storage_pool`, `network`,
   `pcie_passthrough`) or are added here when a new name is
   warranted.
2. **Tags come from the do_* table above.** Tagging a task with
   anything outside the table requires this document to grow the
   tag first.
3. **Make targets follow `<module>-<sub>-<op>`.** The dash
   spelling for Make follows the spec's existing rule
   ("Make targets use `-` separators; role names use `_`
   separators"); the verb at the tail (`-setup`, `-cleanup`) is
   the operation kind in Make form.

## Configuration flow

A module's options flow to Ansible variables through Kconfig
exclusively. A symbol declared `output yaml` in the module's Kconfig
is emitted directly to `.extra_vars_auto.yaml` by the kconfig solver
and from there to `extra_vars.yaml`. The Kconfig symbol name maps
1:1 to the YAML key (the `CONFIG_` prefix is dropped, the rest
lowercased):

| Kconfig symbol | YAML key |
|---|---|
| `CONFIG_ANSIBLE_CONFIG_PATH` | `ansible_config_path` |
| `CONFIG_MIRROR_BLKTESTS_URL` | `mirror_blktests_url` |

All of a module's emitted symbols share the module's name as their
prefix: a module named `<name>` declares its YAML-bound symbols as
`CONFIG_<NAME_UPPER>_<VAR>` so the resulting YAML keys read
`<name>_<var>`.

A symbol always declared in the Kconfig (always has a default,
always emits) keeps its user prompt visible only when a parent gate
is set via the `string "..." if <GATE>` form:

```
config ANSIBLE_CONFIG_PATH
        string "Ansible configuration file" if ANSIBLE_CONFIG_PATH_CUSTOM
        output yaml
        default "$(TOPDIR_PATH)/ansible.cfg"
```

Hidden symbols (no prompt at all) are valid for values that should
flow to playbooks without being user-facing. Dynamic defaults can
use `default $(shell, <script>)` for values computed at parse time.

A module's variables that flow to ansible MUST be declared with
`output yaml` in the module's Kconfig and reach `extra_vars.yaml`
through the kconfig solver. The Makefile MUST NOT push those values
into ansible by any other path: no `ANSIBLE_EXTRA_ARGS += foo=$(CONFIG_X)`
appends, no `EXTRA_VAR_FRAGMENTS` writes under `.extra_vars.d/`, no
inline `--extra-vars foo=...` on the `ansible-playbook` command line.
Make-side variables are still fine for Make-time use (prerequisite
target names, recipe wiring) — they just don't get a second life as
ansible vars. Commit `373df3ee` ("linux-mirror: migrate all mirror
makefile vars to kconfig") is the canonical precedent for the
single-path Kconfig flow this rule enforces.

### Variable namespace collisions with ansible

Ansible reserves a set of variable names (see
`ansible/lib/ansible/constants.py:INTERNAL_STATIC_VARS` —
`ansible_config_file`, `ansible_inventory_sources`, `ansible_forks`,
`inventory_file`, `inventory_dir`, `inventory_hostname`, `groups`,
`hostvars`, `playbook_dir`, `role_path`, and more). A subset is
**actively overridden** at task evaluation by `vars/manager.py:457`
and `inventory/data.py:198`: when a kdevops `output yaml` symbol maps
to one of these names, ansible silently overwrites our value with
its own (often empty in cold-tree scenarios). The rest only emit a
`warn_if_reserved` warning but the kdevops value passes through.

A module whose name shares a prefix with reserved names (e.g.
`ansible_config`, `ansible_inventory`, `inventory`) MUST consult
`INTERNAL_STATIC_VARS` and pick var suffixes that don't collide.
For the canonical example: an `ansible_config` module's "path to
ansible.cfg" variable cannot be `ANSIBLE_CONFIG_FILE` (the YAML key
`ansible_config_file` is overridden); use `ANSIBLE_CONFIG_PATH`
instead. The module README documents which collisions it dodged.

Before adding any new `output yaml` symbol, grep
`ansible/lib/ansible/constants.py` for `INTERNAL_STATIC_VARS` and the
explicit-override call sites (`vars/manager.py`, `inventory/data.py`,
`inventory/host.py`) to confirm the symbol name doesn't collide.

See `docs/kconfig-integration.md` for the `output yaml` mechanism.

### When `output yaml` silently does not emit

`output yaml` is the single canonical path from Kconfig to ansible
extra_vars, but two corner cases leave the consumer with no value —
documented in [the `kdevops_enable_terraform`
thread](https://lore.kernel.org/kdevops/60215220-9833-40d2-a29e-92a5917d20c2@oracle.com/)
and the workaround landed as commit `04417817` ("devconfig: add a
default for kdevops_enable_terraform"):

1. **Hidden bool** (`bool` without a prompt, no unconditional
   `default`): when the value evaluates to the implicit `n`, kconfig
   omits the symbol from `.config` entirely. The solver has nothing
   to emit; the YAML key is absent. (Prompted symbols always appear
   in `.config` as either `=y` or `# CONFIG_X is not set`, so they
   always emit a value.)
2. **Symbol inside `if X` ... `endif`**: when the gate `X` is false
   the symbol is not declared. `output yaml` is unreachable; the
   YAML key is absent.

In both cases a role observing the undefined var via `{{ foo }}` or
`when: foo` errors with `'foo' is undefined`. This is not a role
bug — it is the documented behaviour of `output yaml`.

A module facing one of these gaps picks one of four fixes, in
preference order:

1. **Promote the symbol.** Add a `bool "..."` / `string "..."` prompt
   on the Kconfig declaration. Forces `.config` to record it; the
   YAML key always emits. Use when the var is a real user-facing knob.
2. **Lift the symbol out of the gate.** Move the declaration outside
   `if X` ... `endif` (the gate can still control `default`s inside).
   Use when the var conceptually exists in every tree state.
3. **Add an unconditional `default`.** A hidden bool ending with
   `default n` (after the conditional defaults) always evaluates to a
   value the solver emits. Use when prompting would clutter
   `menuconfig`.
4. **Default at the consumer.** Reference the var with
   `{{ foo | default(false) }}` or `when: foo | default(false) | bool`.
   Use when the var legitimately may be absent (workflow gate inside
   another module's `if`), or when the producing Kconfig is owned by
   a module not migrated yet.

The pre-spec workaround — adding the missing var to a role's
`defaults/main.yml` (as commit `04417817` did) — works but is
**discouraged going forward**: it forces every consuming role to
carry an identical default, fragments the tree-wide namespace into
per-role copies, and is what ansible-lint's
`var-naming[no-role-prefix]` rule penalises.

A role's `defaults/main.yml` SHOULD only declare role-private vars
(prefixed with the role name). Tree-wide vars come from
`extra_vars.yaml` via the Kconfig path; gaps in that path are filled
by the consumer-side `| default(...)` pattern, not by re-declaring
the var per role.

## Integration contract

The module's `Makefile` may append to project-wide variables:

| Variable | Effect |
|---|---|
| `HELP_TARGETS += <name>-help-menu` | Listed by `make help`. |
| `LOCALHOST_SETUP_WORK += <target>` | Runs on `make controller-setup`. |
| `KDEVOPS_BRING_UP_DEPS_EARLY += <target>` | Runs before guest provisioning. |
| `KDEVOPS_BRING_UP_DEPS += <target>` | Runs as part of `make bringup`. |
| `KDEVOPS_BRING_UP_LATE_DEPS += <target>` | Runs at the end of `make bringup`. |
| `KDEVOPS_INSTALL_TARGETS += <target>` | Listed by `make install`. |

User-facing Make targets MUST:
- be appended to `PHONY`;
- depend on `$(KDEVOPS_EXTRA_VARS)` (or `env`) when they invoke
  `ansible-playbook`.

**Every rule in a module's Makefile that invokes `ansible-playbook`
— PHONY targets AND file rules — MUST go through the
`run-ansible-playbook` macro defined in the top-level Makefile.**
Direct `$(Q)ansible-playbook` is legacy and is migrated away as
each module moves to the canonical layout.

```
<name>: $(KDEVOPS_NODES)
	$(call run-ansible-playbook, \
		$(KDEVOPS_PLAYBOOKS_DIR)/<name>.yml \
		--extra-vars=@./extra_vars.yaml $(LIMIT_HOSTS))
```

The macro adapts to the active callback. When
`CONFIG_ANSIBLE_CONFIG_CALLBACK_PLUGIN_LUCID=y` it wraps with
`script(1)` so the child sees a real pty and lucid's dynamic mode
engages (in-place TUI, ANSI cursor control). For any other callback
it pipes through `tee` with `set -o pipefail`, producing plain
scrolling output. Both paths capture the terminal replay under
`$(KDEVOPS_LOG_DIR)`.

The first invocation in a fresh tree may run before `ansible.cfg`
exists (the rule that generates it must still use the macro). The
macro is safe in that case: `script(1)` allocates the pty
regardless; ansible-playbook falls back to its default callback when
no `ansible.cfg` is readable; the log is still captured.

**Literal commas at the call site** are consumed by `$(call)` as
argument separators (see make.texi "Call Function"). Commas coming
from expanded variables (`$(LIMIT_HOSTS) = --limit a,b,c`) are
protected by Make's argument parser and need no escaping. A literal
comma in the macro args — most commonly `--inventory localhost,`
— must use the `$(comma)` helper from `Makefile.extra_vars`:

```
$(call run-ansible-playbook, \
	--connection=local \
	--inventory localhost$(comma) \
	$(KDEVOPS_PLAYBOOKS_DIR)/<name>.yml \
	--extra-vars=@./extra_vars.yaml)
```

The Makefile MUST NOT reach into other modules' internals.

## Ansible

The playbook is the entry point invoked by the module's Make targets.
The role's `defaults/main.yml` documents every variable the role
consumes. All `playbooks/roles/*/defaults/main.yml` are prerequisites
of `extra_vars.yaml`.

The role's task files use Ansible tags from the `do_*` task
vocabulary so `ansible-playbook --tags <do_*>` selects the right
subset.

## Lint

A module migration runs two scoped lint gates from `make`. Neither
touches anything outside the module's paths; tree-wide linting stays
in `make style` until the whole tree is clean enough to enforce
globally.

```
make ansible-lint-module MODULE=<name>
make python-lint-module  MODULE=<name>
```

`ansible-lint-module` invokes `ansible-lint --profile=production
--fix=all` on `playbooks/<name>.yml` and `playbooks/roles/<name>/`.
`python-lint-module` runs `black` and `ruff check --fix` on every
`*.py` under `modules/<name>/`.

Fixes land in the migration commit when same-purpose, otherwise as a
follow-up `<name>: lint cleanups` commit.

## MAINTAINERS

Every module has an entry in the top-level `MAINTAINERS` file under
its canonical name (uppercase). The entry covers every path the
module owns:

```
<NAME-UPPERCASE>
M:	<Maintainer Name> <email>
L:	kdevops@lists.linux.dev
S:	Maintained
T:	git https://github.com/linux-kdevops/kdevops.git
F:	modules/<name>/
F:	playbooks/<name>.yml
F:	playbooks/roles/<name>/
```

For modules with sub-modules, the `F:` glob `modules/<name>/` covers
the nested `modules/` paths and `playbooks/roles/<name>/` covers
every nested sub-role under the parent role's directory. No
additional `F:` lines are needed for sub-modules unless the
sub-module owns a path outside those two roots.

## README

Required sections, in order:

1. **Purpose** — one paragraph.
2. **Tasks** — table of tasks the module implements and the Make
   target that invokes each.
3. **Configuration** — list of `CONFIG_<NAME>_*` knobs, hidden or
   user-facing.
4. **Layout** — paths the module owns.
5. **Sub-modules** — one line each, with their Kconfig switch.
6. **Dependencies** — other modules this one assumes.

User-facing prose (tutorials, how-to guides) belongs in
`docs/<name>.md`, not the module README.

## Docs

A module's user-facing documentation lives at `docs/<name>.md`. The
filename is the canonical module name verbatim — no `kdevops-`
prefix, no `-ansible-role` suffix, no project namespace decoration.
Same rule as for the module's Kconfig path, Makefile path, playbook
filename, and role directory: `<name>` is identical across them all.

The document targets users (configuration knobs, workflows, examples),
not contributors (the `README.md` inside the module covers that).
If the module is small enough that there is nothing user-facing to
say, the doc may be omitted; otherwise it MUST live at
`docs/<name>.md`.

MAINTAINERS gains an `F: docs/<name>.md` line for the module when
the doc exists.

## Tree sample

```
modules/libvirt/
├── Kconfig
├── Makefile
├── README.md
├── scripts/
│   └── libvirt_pool.sh
├── cxl/
│   ├── Kconfig
│   └── README.md
├── user/                              sub-module (sudo opt-in)
│   ├── Makefile                       registers libvirt-user-setup
│   └── README.md
└── pcie_passthrough/                  sub-module with sub-sub-modules
    ├── Kconfig
    ├── Makefile
    ├── README.md
    ├── verify/
    │   └── README.md
    └── setup/                         sub-sub-module (sudo opt-in)
        ├── Makefile
        └── README.md

playbooks/libvirt.yml                  one entry-point playbook
playbooks/roles/libvirt/
├── defaults/main.yml
├── tasks/main.yml                     orchestrates: includes verify always,
│                                      sub-roles tag-gated
├── prep_localhost/                    sub-role (internal helper)
│   ├── defaults/main.yml
│   └── tasks/main.yml
├── user/                              sub-module's role
│   ├── verify/tasks/main.yml          non-sudo state check
│   └── setup/tasks/main.yml           sudo work
└── pcie_passthrough/                  sub-module's role
    ├── tasks/main.yml                 cascades into verify+setup
    ├── verify/tasks/main.yml
    └── setup/tasks/main.yml
```

## Not modules

- Build-system helpers under `scripts/*.Makefile`: `build`, `ci`,
  `style`, `refs`, `archive`, `defconfig`, `firstconfig`,
  `dynamic-*-kconfig`, `gen-*`, `kconfig*`, `objects`, `provision`,
  `linux-ab-testing`, `tests`, `kotd`, `ansible`. No Kconfig, no
  playbook, no role.
- Project-wide Makefiles at the repo root: `Makefile.kdevops`,
  `Makefile.subtrees`, `Makefile.min_deps`, `Makefile.extra_vars`,
  `Makefile.local`.
- `workflows/common/`, `workflows/demos/`, `workflows/kdevops/`.
- Sub-roles (see above).

## Cross-references

- `docs/kconfig-integration.md` — `output yaml` mechanism.
- `docs/how-extra-vars-generated.md` — `extra_vars.yaml` generation.
- `docs/ansible-roles.md` — role conventions.
