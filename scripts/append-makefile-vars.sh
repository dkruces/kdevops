#!/bin/bash

STR=""

if [[ $# -eq 0 ]]; then
	echo \"\"
	exit 0
fi

# First argument is the prefix (e.g., ~/.ssh/config_kdevops_)
STR="${1}"
shift

# Second argument: if it looks like a SHA256 hash (>=40 hex chars),
# use only the first 8 characters to match the SSH config / tfvars
# templates. Otherwise (IPs, paths, refs, URL fragments), pass it
# through verbatim — the older :0:8 truncation mangled those.
if [[ ${#1} -gt 0 ]]; then
	if [[ "$1" =~ ^[a-fA-F0-9]{40,}$ ]]; then
		STR="${STR}${1:0:8}"
	else
		STR="${STR}${1}"
	fi
	shift
fi

# Append any remaining arguments as-is
while [[ ${#1} -gt 0 ]]; do
	STR="${STR}${1}"
	shift
done

echo $STR
