#!/usr/bin/env python3
"""Lightweight HTTP proxy for Claude CLI.

Runs on the HOST machine and wraps ``claude -p`` calls. The Docker-based
celery worker calls this proxy instead of running the CLI directly, since
the CLI needs macOS Keychain access for OAuth authentication.

Usage:
    python3 scripts/claude-proxy.py          # starts on port 8019
    python3 scripts/claude-proxy.py --port 8019

The celery worker calls:
    POST http://host.docker.internal:8019/generate
    Body: {"prompt": "...", "system_prompt": "...", "model": "sonnet", "max_turns": 1, "timeout": 120}

Requires only Python 3.9+ stdlib — no pip dependencies needed.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

DEFAULT_PORT = 8019
DEFAULT_MODEL = "sonnet"


class ClaudeProxyHandler(BaseHTTPRequestHandler):
    """Handle POST /generate requests by calling claude -p."""

    def do_GET(self):
        """Health check endpoint."""
        if self.path == "/health":
            self._json_response(200, {"status": "ok", "service": "claude-proxy"})
        else:
            self._json_response(404, {"error": "not found"})

    def do_POST(self):
        """Handle /generate requests."""
        if self.path != "/generate":
            self._json_response(404, {"error": "not found"})
            return

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            params = json.loads(body)
        except (json.JSONDecodeError, ValueError) as e:
            self._json_response(400, {"error": f"Invalid JSON: {e}"})
            return

        prompt = params.get("prompt", "")
        system_prompt = params.get("system_prompt")
        model = params.get("model", DEFAULT_MODEL)
        max_turns = params.get("max_turns", 1)
        timeout = params.get("timeout", 120)

        if not prompt:
            self._json_response(400, {"error": "prompt is required"})
            return

        # Build claude -p command
        cmd = [
            "claude",
            "-p", prompt,
            "--model", str(model),
            "--output-format", "json",
            "--max-turns", str(max_turns),
        ]

        # System prompt via temp file
        sys_prompt_file = None
        if system_prompt:
            sys_prompt_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            )
            sys_prompt_file.write(system_prompt)
            sys_prompt_file.close()
            cmd.extend(["--append-system-prompt-file", sys_prompt_file.name])

        env = {**os.environ, "NO_COLOR": "1"}

        print(f"[claude-proxy] Calling: claude -p (model={model}, prompt_len={len(prompt)}, "
              f"system_prompt={'yes' if system_prompt else 'no'})")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )

            if result.returncode != 0:
                error_msg = result.stderr[:500] or result.stdout[:500]
                print(f"[claude-proxy] CLI error (exit={result.returncode}): {error_msg[:200]}")
                self._json_response(502, {
                    "error": f"Claude CLI exited with code {result.returncode}",
                    "stderr": result.stderr[:500],
                    "stdout": result.stdout[:500],
                })
                return

            # Parse JSON output
            stdout = result.stdout.strip()
            try:
                parsed = json.loads(stdout)
            except json.JSONDecodeError:
                # Try finding JSON line
                for line in stdout.split("\n"):
                    line = line.strip()
                    if line.startswith("{"):
                        try:
                            parsed = json.loads(line)
                            break
                        except json.JSONDecodeError:
                            continue
                else:
                    self._json_response(502, {
                        "error": "Claude CLI returned non-JSON",
                        "stdout": stdout[:500],
                    })
                    return

            result_text = parsed.get("result", "")
            session_id = parsed.get("session_id", "")
            print(f"[claude-proxy] Success: {len(result_text)} chars, session={session_id}")

            self._json_response(200, {
                "result": result_text,
                "session_id": session_id,
                "raw": parsed,
            })

        except subprocess.TimeoutExpired:
            print(f"[claude-proxy] Timeout after {timeout}s")
            self._json_response(504, {"error": f"Claude CLI timed out after {timeout}s"})

        except FileNotFoundError:
            print("[claude-proxy] ERROR: 'claude' command not found. Is Claude Code CLI installed?")
            self._json_response(500, {"error": "claude command not found"})

        except Exception as e:
            print(f"[claude-proxy] Unexpected error: {e}")
            self._json_response(500, {"error": str(e)})

        finally:
            if sys_prompt_file:
                try:
                    os.unlink(sys_prompt_file.name)
                except OSError:
                    pass

    def _json_response(self, status_code, data):
        """Send a JSON response."""
        body = json.dumps(data).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        """Suppress default request logging (we have our own)."""
        pass


def main():
    parser = argparse.ArgumentParser(description="Claude CLI HTTP Proxy")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Port to listen on")
    args = parser.parse_args()

    # Verify claude CLI is available
    try:
        result = subprocess.run(["claude", "--version"], capture_output=True, text=True, timeout=5)
        version = result.stdout.strip()
        print(f"[claude-proxy] Claude CLI: {version}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("[claude-proxy] ERROR: 'claude' command not found. Install Claude Code CLI first.")
        sys.exit(1)

    # Verify auth
    try:
        result = subprocess.run(
            ["claude", "auth", "status"],
            capture_output=True, text=True, timeout=10,
        )
        auth_info = json.loads(result.stdout.strip())
        print(f"[claude-proxy] Auth: {auth_info}")
        if not auth_info.get("loggedIn"):
            print("[claude-proxy] WARNING: Claude CLI is not logged in!")
    except Exception as e:
        print(f"[claude-proxy] Could not check auth: {e}")

    server = HTTPServer(("0.0.0.0", args.port), ClaudeProxyHandler)
    print(f"[claude-proxy] Listening on http://0.0.0.0:{args.port}")
    print(f"[claude-proxy] Docker workers use: http://host.docker.internal:{args.port}/generate")
    print(f"[claude-proxy] Press Ctrl+C to stop")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[claude-proxy] Shutting down...")
        server.shutdown()


if __name__ == "__main__":
    main()
