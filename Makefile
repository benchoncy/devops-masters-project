python = poetry run python
tf_dir = infra/

# General
help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  install       to install dependencies"
	@echo "  test          to run tests"
	@echo "  setup         to install dependencies, configure metaflow and activate virtual environment"
	@echo "  lint          to run pre-commit hooks"
	@echo "  tf            to run terraform"
	@echo "  tf.init       to initialize terraform"
	@echo "  tf.plan       to plan terraform"
	@echo "  tf.apply      to apply terraform"
	@echo "  tf.destroy    to destroy terraform"
	@echo "  metaflow.configure to configure metaflow"

lint:
	pre-commit run --color always --all-files

install: py.install

test: py.test

setup: install metaflow.configure py.activate

# Python
py.install:
	poetry install

py.activate:
	poetry shell

py.test:
	${python} -m pytest

# Terraform
tf: tf.init tf.plan tf.apply

tf.init:
	cd ${tf_dir} && terraform init

tf.plan:
	cd ${tf_dir} && terraform plan -out tfplan

tf.apply:
	cd ${tf_dir} && terraform apply tfplan

tf.destroy:
	cd ${tf_dir} && terraform destroy

# Metaflow
metaflow.configure:
	cp ${tf_dir}/config/config_batch.json ~/.metaflowconfig/config_mstr_batch.json
	cp ${tf_dir}/config/config_batch_testing.json ~/.metaflowconfig/config_mstr_batch_testing.json
	cp ${tf_dir}/config/config_k8s.json ~/.metaflowconfig/config_mstr_k8s.json
