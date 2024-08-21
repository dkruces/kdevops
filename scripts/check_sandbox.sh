#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

usage() {
    echo "Usage: $0 [--presence|-p] [--dirname|-d]"
    exit 1
}

presence() {
    # Check if a directory matching runconf* exists
    if [ -d "${CONFIG_DIR_NAME}" ]; then
        echo y
    else
        echo n
    fi
}

dirname() {
    echo "${CONFIG_DIR_NAME}"
}

# Initialize the options
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --presence|-p)
            presence
            exit
            ;;
        --dirname|-d)
            dirname
            exit
            ;;
        *)
            usage
            ;;
    esac
done

# If no option was provided, show usage instructions
usage
