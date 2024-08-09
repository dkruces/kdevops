#!/bin/bash

# Script to clean up all domains and storage pools with user confirmation

# Function to prompt the user for confirmation
confirm_action() {
  local action=$1
  local name=$2
  read -p "Are you sure you want to $action $name? (y/n): " choice
  case "$choice" in
    y|Y ) return 0 ;; # Proceed with action
    n|N ) echo "Skipping $name" ; return 1 ;; # Skip action
    * ) echo "Invalid choice" ; return 1 ;; # Invalid input
  esac
}

# Destroy and undefine all domains
echo "Cleaning up all domains..."
for domain in $(sudo virsh list --all --name); do
  if [ -n "$domain" ]; then
    if confirm_action "destroy and undefine" "$domain"; then
      echo "Destroying domain: $domain"
      sudo virsh destroy "$domain" 2>/dev/null
      echo "Undefining domain: $domain"
      sudo virsh undefine "$domain"
    fi
  fi
done

# Destroy and delete all storage pools
echo "Cleaning up all storage pools..."
for pool in $(sudo virsh pool-list --all --name); do
  if [ -n "$pool" ]; then
    if confirm_action "destroy, undefine, and delete" "$pool"; then
      echo "Destroying storage pool: $pool"
      sudo virsh pool-destroy "$pool" 2>/dev/null
      echo "Undefining storage pool: $pool"
      sudo virsh pool-undefine "$pool"
      
      # Check if the pool still exists before attempting to delete it
      if sudo virsh pool-list --all --name | grep -q "$pool"; then
        echo "Deleting storage pool: $pool"
        sudo virsh pool-delete "$pool"
      else
        echo "Storage pool $pool has already been removed or does not exist."
      fi
    fi
  fi
done

echo "Cleanup completed."

