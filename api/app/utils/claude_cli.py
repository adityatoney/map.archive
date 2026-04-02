"""Claude CLI helper — runs ``claude -p`` in headless mode.

Uses the Claude Code CLI (``claude -p``) for non-interactive LLM generation.

Authentication:
  - In Docker: via CLAUDE_CODE_OAUTH_TOKEN env var (Claude Max subscription)
  - On host:   via macOS Keychain (claude.ai login)

Example CLI usage:
    claude -p "<question>" \\
      --append-system-prompt-file prompt.txt \\
      --output-format json \\
      --model sonnet \\
      --max-turns 1
"""

import asyncio
import json
import logging
import os
import tempfile
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

# One-time setup: ensure .claude.json exists with onboarding flag
# (required for headless mode in Docker)
_CLAUDE_JSON_PATH = os.path.expanduser("~/.claude.json")
if not os.path.exists(_CLAUDE_JSON_PATH):
    try:
        os.makedirs(os.path.dirname(_CLAUDE_JSON_PATH), exist_ok=True)
        with open(_CLAUDE_JSON_PATH, "w") as f:
            json.dump({"hasCompletedOnboarding": True}, f)
    except OSError:
        pass


async def claude_generate(
    prompt: str,
    system_prompt: str | None = None,
    model: str | None = None,
    max_turns: int = 1,
    timeout: int = 120,
) -> dict[str, Any]:
    """Run ``claude -p`` and return the parsed JSON result.

    Args:
        prompt: The user prompt to send.
        system_prompt: Optional system prompt (written to temp file).
        model: Model alias (e.g. "sonnet") or full name. Defaults to config.
        max_turns: Max agentic turns (1 = single response, no tools).
        timeout: Subprocess timeout in seconds.

    Returns:
        dict with keys:
          - result: str — the text response from Claude
          - session_id: str — CLI session ID
          - raw: dict — full parsed JSON from --output-format json

    Raises:
        RuntimeError: If the CLI process fails or times out.
    """
    settings = get_settings()
    model = model or settings.ANTHROPIC_MODEL

    # Build the CLI command
    cmd = [
        "claude",
        "-p", prompt,
        "--model", model,
        "--output-format", "json",
        "--max-turns", str(max_turns),
    ]

    # System prompt via a temp file (avoids shell quoting issues)
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
        model,
        len(prompt),
        bool(system_prompt),
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
            raise RuntimeError(
                f"Claude CLI timed out after {timeout}s"
            )

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()

        if process.returncode != 0:
            logger.error(
                "Claude CLI failed (exit=%d)\nstderr: %s\nstdout: %s",
                process.returncode,
                stderr_text[:500],
                stdout_text[:500],
            )
            raise RuntimeError(
                f"Claude CLI exited with code {process.returncode}: "
                f"{stderr_text[:200] or stdout_text[:200]}"
            )

        # Parse JSON output
        try:
            parsed = json.loads(stdout_text)
        except json.JSONDecodeError:
            # Sometimes the output has extra lines before the JSON
            # Try to find the JSON object in the output
            for line in stdout_text.split("\n"):
                line = line.strip()
                if line.startswith("{"):
                    try:
                        parsed = json.loads(line)
                        break
                    except json.JSONDecodeError:
                        continue
            else:
                logger.error(
                    "Claude CLI returned non-JSON output: %s", stdout_text[:500]
                )
                raise RuntimeError(
                    f"Claude CLI returned non-JSON: {stdout_text[:200]}"
                )

        result_text = parsed.get("result", "")
        session_id = parsed.get("session_id", "")

        logger.info(
            "Claude CLI response: %d chars, session=%s",
            len(result_text),
            session_id,
        )

        return {
            "result": result_text,
            "session_id": session_id,
            "raw": parsed,
        }

    finally:
        # Clean up temp file
        if sys_prompt_file:
            try:
                os.unlink(sys_prompt_file.name)
            except OSError:
                pass
