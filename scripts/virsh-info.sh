#!/bin/bash

# Get all active and inactive domains
domains=$(sudo virsh list --all --name)

echo "Domain Name, Disk Device, Pool Name, Volume Path"
echo "------------------------------------------------"

# Iterate over each domain
for domain in $domains; do
  # Get the domain's XML configuration
  xml=$(sudo virsh dumpxml "$domain")

  # Extract the source file paths from the XML
  source_files=$(echo "$xml" | grep -oP "(?<=<source file=\').*?(?=\')" | tr -d "'")

  # Iterate over each source file
  for source_file in $source_files; do
    # Skip if the source_file is empty or malformed
    if [[ -z "$source_file" ]]; then
      continue
    fi

    pool_name=""

    # Iterate over each storage pool to find the associated volume path
    pools=$(sudo virsh pool-list --all --name)
    for pool in $pools; do
      # Iterate over volumes in the pool
      volumes=$(sudo virsh vol-list --pool "$pool" | tail -n +3 | awk '{print $2}')

      for volume_path in $volumes; do
        # Check if the volume path is a substring of the source_file
        if [[ "$source_file" == *"$volume_path"* ]]; then
          pool_name="$pool"
          break 2
        fi
      done
    done

    # Display the relationship if the pool was found
    if [ ! -z "$pool_name" ]; then
      echo "$domain, $source_file, $pool_name, $source_file"
    else
      echo "$domain, $source_file, UNKNOWN_POOL, $source_file"
    fi
  done
done

