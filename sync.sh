#!/usr/bin/env bash
rsync -avz "dskbg004:/data1-xfs/dagomez/kdevops/*.log" .

rsync -avz \
	dskbg004:/data1-xfs/dagomez/kdevops/.config \
	dskbg004:/data1-xfs/dagomez/kdevops/.extra_vars_auto.yaml \
	dskbg004:/data1-xfs/dagomez/kdevops/extra_vars.yaml \
	.

rsync -avz \
	dskbg004:/data1-xfs/dagomez/kdevops/guestfs \
	.
