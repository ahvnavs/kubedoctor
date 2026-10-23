"""Optional external context. Failures here never change the diagnosis."""

from dataclasses import replace
import json
import os
from typing import Any
from urllib import parse, request

from .models import Diagnosis, Evidence


class EnrichmentError(RuntimeError):
    pass


def _get_json(url: str, headers: dict[str, str] | None = None, body: bytes | None = None) -> dict[str, Any]:
    req = request.Request(url, data=body, headers=headers or {}, method="POST" if body else "GET")
    try:
        with request.urlopen(req, timeout=8) as response:
            return json.load(response)
    except Exception as exc:
        raise EnrichmentError(str(exc)) from exc


def add_prometheus_context(items: list[Diagnosis], base_url: str) -> list[Diagnosis]:
    output = []
    for item in items:
        pod = item.resource.removeprefix("pod/").replace('"', r'\"')
        query = f'max(container_memory_working_set_bytes{{pod="{pod}",container!=""}})'
        url = f"{base_url.rstrip('/')}/api/v1/query?{parse.urlencode({'query': query})}"
        payload = _get_json(url)
        results = payload.get("data", {}).get("result", [])
        if results:
            value = float(results[0]["value"][1]) / 1024 / 1024
            evidence = (*item.evidence, Evidence("prometheus", f"recent memory usage={value:.1f} MiB"))
            item = replace(item, evidence=evidence)
        output.append(item)
    return output


def add_llm_explanations(items: list[Diagnosis]) -> list[Diagnosis]:
    endpoint = os.getenv("KUBEDOCTOR_LLM_URL")
    token = os.getenv("KUBEDOCTOR_LLM_API_KEY")
    model = os.getenv("KUBEDOCTOR_LLM_MODEL")
    if not endpoint or not token or not model:
        raise EnrichmentError(
            "set KUBEDOCTOR_LLM_URL, KUBEDOCTOR_LLM_API_KEY, and KUBEDOCTOR_LLM_MODEL"
        )
    output = []
    for item in items:
        prompt = (
            "Explain this Kubernetes diagnosis in at most three plain-language sentences. "
            "Do not invent facts or commands.\n"
            f"Title: {item.title}\nEvidence: {[e.detail for e in item.evidence]}\n"
            f"Recommended command: {item.fix_command}"
        )
        body = json.dumps({"model": model, "temperature": 0, "messages": [
            {"role": "system", "content": "You explain Kubernetes failures accurately and concisely."},
            {"role": "user", "content": prompt},
        ]}).encode()
        payload = _get_json(endpoint, {
            "Authorization": f"Bearer {token}", "Content-Type": "application/json"
        }, body)
        try:
            explanation = payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, AttributeError) as exc:
            raise EnrichmentError("LLM response did not contain an explanation") from exc
        output.append(replace(item, explanation=explanation))
    return output
