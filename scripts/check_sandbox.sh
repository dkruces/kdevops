#!/bin/bash
# SPDX-License-Identifier: copyleft-next-0.3.1

usage() {
    echo "Usage: $0 [--presence|-p] [--dirname|-d]"
    exit 1
}

presence() {
    if [ -d "${SANDBOXDIR}" ]; then
        echo y
    else
        echo n
    fi
}

dirname() {
    echo "${SANDBOXDIR}"
}

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

usage
