python = poetry run python
tf_dir = infra/

# General
lint:
	pre-commit run --color always --all-files

install: py.install

test: py.test

# Python
py.install:
	poetry update

py.activate:
	poetry shell

py.test:
	${python} -m pytest

# Terraform
tf.init:
	cd ${tf_dir} && terraform init

tf.plan:
	cd ${tf_dir} && terraform plan -out tfplan

tf.apply:
	cd ${tf_dir} && terraform apply tfplan

tf.destroy:
	cd ${tf_dir} && terraform destroy
