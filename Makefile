python = poetry run python
tf_dir = infra/

# General
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
	cp ${tf_dir}/config/config_k8s.json ~/.metaflowconfig/config_mstr_k8s.json
