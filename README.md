# KubeDoctor

KubeDoctor is a focused command-line tool that explains common Kubernetes pod failures and prints practical `kubectl` fixes. The project is being built in tested phases; live cluster diagnosis arrives in the next phase.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
kubedoctor --help
pytest
```

