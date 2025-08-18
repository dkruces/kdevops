# Guestfs Destroy Tasks

This directory contains idempotent Ansible tasks for destroying VMs, storage, and networks managed by kdevops with configurable destroy modes.

## Task Files

### `main.yml`
Main entry point that orchestrates the destroy process based on Kconfig destroy mode settings.

### `hosts.yml` 
Targeted destroy functionality - removes only VMs defined in inventory hosts file (GUESTFS_DESTROY_TARGETED mode).

### `vms.yml`
Pattern-based and comprehensive VM destruction (GUESTFS_DESTROY_PATTERN_BASED and GUESTFS_DESTROY_COMPREHENSIVE modes).

### `storage.yml`
Storage pool and volume cleanup with configurable patterns.

### `networks.yml`
Network cleanup with preservation of critical networks.

### `comprehensive.yml`
Complete system cleanup including logs, configs, and artifacts (GUESTFS_DESTROY_COMPREHENSIVE mode only).

## Configuration via Kconfig

Destroy behavior is configured through `make menuconfig` under "Guestfs destroy mode":

### GUESTFS_DESTROY_TARGETED (Default)
- Destroys only VMs defined in inventory hosts file  
- Maintains full backward compatibility
- Preserves manually created libvirt resources

### GUESTFS_DESTROY_PATTERN_BASED  
- Uses configurable regex patterns to match resources
- Customizable VM, storage pool, and network patterns
- More flexible than targeted mode while remaining safe

### GUESTFS_DESTROY_COMPREHENSIVE
- Destroys ALL VMs, storage pools, and networks
- Uses preservation patterns to protect critical infrastructure
- Most thorough cleanup possible

## Configuration Variables

These variables are automatically set based on Kconfig selections:

```yaml
# Pattern variables (configured via menuconfig)
guestfs_destroy_vm_pattern: "{{ guestfs_destroy_vm_pattern }}"
guestfs_destroy_pool_pattern: "{{ guestfs_destroy_pool_pattern }}"  
guestfs_destroy_network_pattern: "{{ guestfs_destroy_network_pattern }}"
guestfs_preserve_pool_pattern: "{{ guestfs_preserve_pool_pattern }}"

# Debug and control variables  
guestfs_debug_destroy: "{{ guestfs_debug_destroy }}"
guestfs_purge_comprehensive: "{{ guestfs_purge_comprehensive }}"
```

## Usage

### Configuration
```bash
make menuconfig  # Navigate to "Guestfs destroy mode" 
make             # Apply configuration
```

### Execution
```bash
make destroy     # Uses configured destroy mode
```

## Default Pattern Examples

### VM Patterns
```
.*[Kk][Dd][Ee][Vv][Oo][Pp][Ss].*|.*demo.*  # Matches kdevops/demo VMs
```

### Storage Pool Patterns
```
.*[Kk][Dd][Ee][Vv][Oo][Pp][Ss].*|.*demo.*|.*vm.*|.*guest.*|.*temp.*  # Development pools
(home|users|data|backup|important)  # Preserved pools
```

### Network Patterns
```
.*[Kk][Dd][Ee][Vv][Oo][Pp][Ss].*|.*demo.*|.*vm.*|.*guest.*|.*temp.*  # Development networks
```

## Idempotency

All tasks are designed to be idempotent:

- Only act on resources that actually exist
- Use `ignore_errors: true` for operations that may legitimately fail  
- Check resource states before attempting operations
- Safe to run multiple times

## Safety Features

- Default targeted mode maintains backward compatibility
- Pattern-based filtering prevents accidental deletion  
- Preservation patterns protect critical infrastructure
- Multiple fallback strategies for different libvirt versions
- Comprehensive debug output when enabled

## Mode Selection Logic

The destroy mode is automatically determined from Kconfig settings:

1. **Targeted mode**: Default, no special configuration needed
2. **Pattern-based mode**: When pattern variables are configured
3. **Comprehensive mode**: When `GUESTFS_DESTROY_COMPREHENSIVE=y`
