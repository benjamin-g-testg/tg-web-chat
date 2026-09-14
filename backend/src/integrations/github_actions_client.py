"""Minimal GitHub Actions API client used by the orchestration layer."""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings


class GitHubActionsError(RuntimeError):
    """Raised when GitHub rejects a dispatch request."""


def dispatch_workflow(event_type: str, payload: dict[str, object]) -> None:
    token = getattr(settings, "GITHUB_DISPATCH_TOKEN", "")
    repository = getattr(settings, "GITHUB_REPOSITORY", "")
    if not token or not repository:
        raise GitHubActionsError("GitHub Actions no está configurado en el backend.")

    url = f"https://api.github.com/repos/{repository}/dispatches"
    body = json.dumps({"event_type": event_type, "client_payload": payload}).encode("utf-8")
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "tg-web-chat-orchestrator",
        },
    )
    try:
        with urlopen(request, timeout=getattr(settings, "GITHUB_API_TIMEOUT", 15)) as response:
            if response.status != 204:
                raise GitHubActionsError(f"GitHub respondió HTTP {response.status}.")
    except (HTTPError, URLError, TimeoutError) as error:
        raise GitHubActionsError("No fue posible disparar el workflow de GitHub.") from error