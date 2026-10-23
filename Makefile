.PHONY: help install check image lab-up lab-verify lab-down

help:
	@printf '%s\n' 'install     Install KubeDoctor with development tools' \
		'check       Run lint and unit tests' \
		'image       Build the non-root CLI image' \
		'lab-up      Create the reproducible kind failures' \
		'lab-verify  Detect all four failures in the live cluster' \
		'lab-down    Delete the kind cluster'

install:
	python -m pip install -e '.[dev]'

check:
	ruff check .
	pytest

image:
	docker build --tag kubedoctor:local .

lab-up:
	scripts/lab.sh up

lab-verify:
	scripts/lab.sh verify

lab-down:
	scripts/lab.sh down

