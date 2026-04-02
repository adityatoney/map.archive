"""Claude LLM helper — calls ``claude -p`` via the host proxy.

In Docker, the CLI can't access macOS Keychain for OAuth. Instead, a lightweight
HTTP proxy runs on the host (``scripts/claude-proxy.py``) that wraps ``claude -p``.
The celery worker calls this proxy via ``host.docker.internal``.

If running outside Docker (e.g. local dev), falls back to calling ``claude -p``
directly as a subprocess.

Start the proxy:  ``python3 scripts/claude-proxy.py``
Start Docker:     ``docker compose up -d``
"""

import asyncio
import json
import logging
import os
import tempfile
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

# Proxy URL — the host-side claude-proxy.py service
CLAUDE_PROXY_URL = os.environ.get(
    "CLAUDE_PROXY_URL", "http://host.docker.internal:8019"
)


def _is_docker() -> bool:
    """Detect if running inside Docker."""
    return os.path.exists("/.dockerenv") or os.environ.get("DOCKER_CONTAINER") == "1"


async def claude_generate(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    max_turns: int = 1,
    timeout: int = 120,
) -> dict[str, Any]:
    """Generate text using Claude.

    In Docker: calls the host-side claude-proxy HTTP service.
    On host:   calls ``claude -p`` directly as a subprocess.

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system prompt.
        model: Model alias (e.g. "sonnet") or full name. Defaults to config.
        max_turns: Max agentic turns (1 = single response, no tools).
        timeout: Timeout in seconds.

    Returns:
        dict with keys:
          - result: str — the text response from Claude
          - session_id: str — CLI session ID (empty if proxy)
          - raw: dict — full parsed JSON from CLI

    Raises:
        RuntimeError: If the call fails.
    """
    if _is_docker():
        return await _generate_via_proxy(prompt, system_prompt, model, max_turns, timeout)
    else:
        return await _generate_via_cli(prompt, system_prompt, model, max_turns, timeout)


async def _generate_via_proxy(
    prompt: str,
    system_prompt: str | None,
    model: str | None,
    max_turns: int,
    timeout: int,
) -> dict[str, Any]:
    """Call the host-side Claude proxy HTTP service."""
    settings = get_settings()
    model = model or settings.ANTHROPIC_MODEL

    url = f"{CLAUDE_PROXY_URL}/generate"

    payload = {
        "prompt": prompt,
        "system_prompt": system_prompt,
        "model": model,
        "max_turns": max_turns,
        "timeout": timeout,
    }

    logger.info(
        "Calling Claude proxy at %s (model=%s, prompt_len=%d)",
        url, model, len(prompt),
    )

    async with httpx.AsyncClient(timeout=httpx.Timeout(float(timeout) + 10)) as client:
        try:
            response = await client.post(url, json=payload)
        except httpx.ConnectError as e:
            logger.error(
                "Cannot connect to Claude proxy at %s. "
                "Is scripts/claude-proxy.py running on the host? Error: %s",
                url, str(e)[:200],
            )
            raise RuntimeError(
                f"Cannot connect to Claude proxy at {url}. "
                "Start it with: python3 scripts/claude-proxy.py"
            ) from e
        except httpx.TimeoutException as e:
            raise RuntimeError(f"Claude proxy timed out after {timeout}s") from e

    if response.status_code != 200:
        error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        error_msg = error_data.get("error", response.text[:200])
        logger.error("Claude proxy returned %d: %s", response.status_code, error_msg)
        raise RuntimeError(f"Claude proxy error ({response.status_code}): {error_msg}")

    data = response.json()
    result_text = data.get("result", "")

    logger.info(
        "Claude proxy response: %d chars, session=%s",
        len(result_text), data.get("session_id", ""),
    )

    return data


async def _generate_via_cli(
    prompt: str,
    system_prompt: str | None,
    model: str | None,
    max_turns: int,
    timeout: int,
) -> dict[str, Any]:
    """Call ``claude -p`` directly as a subprocess (host mode)."""
    settings = get_settings()
    model = model or settings.ANTHROPIC_MODEL

    cmd = [
        "claude",
        "-p", prompt,
        "--model", model,
        "--output-format", "json",
        "--max-turns", str(max_turns),
    ]

    sys_prompt_file = None
    if system_prompt:
        sys_prompt_file = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        )
        sys_prompt_file.write(system_prompt)
        sys_prompt_file.close()
        cmd.extend(["--append-system-prompt-file", sys_prompt_file.name])

    logger.info(
        "Calling Claude CLI (model=%s, prompt_len=%d, system_prompt=%s)",
        model, len(prompt), bool(system_prompt),
    )

    env = {**os.environ, "NO_COLOR": "1"}

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise RuntimeError(f"Claude CLI timed out after {timeout}s")

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            logger.error(
                "Claude CLI failed (exit=%d)\nstderr: %s\nstdout: %s",
                process.returncode, stderr_text[:500], stdout_text[:500],
            )
            raise RuntimeError(
                f"Claude CLI exited with code {process.returncode}: "
                f"{stderr_text[:200] or stdout_text[:200]}"
            )

        # Parse JSON output
        try:
            parsed = json.loads(stdout_text)
        except json.JSONDecodeError:
            for line in stdout_text.split("\n"):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        parsed = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            else:
                logger.error("Claude CLI returned non-JSON: %s", stdout_text[:500])
                raise RuntimeError(f"Claude CLI returned non-JSON: {stdout_text[:200]}")

        result_text = parsed.get("result", "")
        session_id = parsed.get("session_id", "")

        logger.info("Claude CLI response: %d chars, session=%s", len(result_text), session_id)

        return {
            "result": result_text,
            "session_id": session_id,
            "raw": parsed,
        }

    finally:
        if sys_prompt_file:
            try:
                os.unlink(sys_prompt_file.name)
            except OSError:
                pass
