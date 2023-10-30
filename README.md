# devops-masters-project

Datasets:
- images: [Household Objects](https://ieee-dataport.org/open-access/annotated-image-dataset-household-objects-robofeihome-team)

# Running Metaflow jobs

1. `make setup`
2. Run flow on select config:
```
METAFLOW_PROFILE=mstr_k8s; python -m {path/to/flow.py} run
```
