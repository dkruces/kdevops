#!/bin/bash
OS_FILE="/etc/os-release"

if [[ ! -f $OS_FILE ]]; then
	echo n
fi

check_distro()
{
	grep -qi $1 $OS_FILE
	if [[ $? -eq 0 ]]; then
		echo y
		exit
	fi
	echo n
	exit
}

check_distro_centos()
{
	# CentOS Stream has both "centos" and references to fedora
	# Check for centos first, excluding if it's actually Fedora (NAME="Fedora")
	grep -qi "NAME=.*Fedora" $OS_FILE
	if [[ $? -eq 0 ]]; then
		echo n
		exit
	fi
	grep -qi centos $OS_FILE
	if [[ $? -eq 0 ]]; then
		echo y
		exit
	fi
	echo n
	exit
}

check_distro_fedora()
{
	# CentOS Stream has ID_LIKE="rhel fedora" but is not actually Fedora
	# Check for CentOS first and exclude it
	grep -qi centos $OS_FILE
	if [[ $? -eq 0 ]]; then
		echo n
		exit
	fi
	# Now check if it's actually Fedora
	grep -qi "NAME=.*Fedora" $OS_FILE
	if [[ $? -eq 0 ]]; then
		echo y
		exit
	fi
	echo n
	exit
}

check_distro_redhat()
{
	grep -qi fedora $OS_FILE
	if [[ $? -eq 0 ]]; then
		echo n
		exit
	fi
	grep -qi redhat $OS_FILE
	if [[ $? -eq 0 ]]; then
		echo y
		exit
	fi
	echo n
	exit
}

check_distro_suse()
{
	grep -vi opensuse $OS_FILE | grep -qi suse
	if [[ $? -eq 0 ]]; then
		echo y
		exit
	fi
	echo n
	exit
}

check_distro_ubuntu()
{
	grep -vi debian $OS_FILE | grep -qi ubuntu
	if [[ $? -eq 0 ]]; then
		echo y
		exit
	fi
	echo n
	exit
}


case $1 in
centos)
	check_distro_centos $1
	;;
debian)
	check_distro $1
	;;
fedora)
	check_distro_fedora $1
	;;
opensuse)
	check_distro $1
	;;
redhat)
	check_distro_redhat $1
	;;
suse)
	check_distro_suse $1
	;;
ubuntu)
	check_distro_ubuntu $1
	;;
*)
	echo n
	exit
esac
