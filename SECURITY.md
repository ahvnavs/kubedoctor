# Security

Please report vulnerabilities through GitHub's private vulnerability reporting instead of a public issue.

KubeDoctor only needs read access to pods and events. The example RBAC policy grants `get` and `list` for those resources and no write verbs. LLM enrichment is opt-in; only the rendered diagnosis, evidence, and suggested command are sent to the configured endpoint. Kubernetes credentials and environment variables are never included in the prompt.

The container runs as UID 10001. Use a read-only filesystem and the supplied service account when running it inside a cluster.
