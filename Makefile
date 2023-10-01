python = poetry run python

install:
	poetry update

activate:
	poetry shell

lint:
	pre-commit run --color always --all-files

test:
	${python} -m pytest
