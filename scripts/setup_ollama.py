#!/usr/bin/env python3
"""
GeoMeasure Studio - Phase 4 AI Copilot
Local Ollama Model Setup & Health Check Utility

Checks local Ollama daemon connectivity, verifies installed models,
and downloads the recommended local model (default: qwen3.5:2b).

Model reference: https://ollama.com/library/qwen3.5:2b
Model weights are managed directly by Ollama (typically ~/.ollama/models).
Weights are NEVER stored or committed to the repository.
"""

import sys
import os
import json
import argparse
import urllib.request
import urllib.error

DEFAULT_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:2b")


def check_ollama_status(base_url: str):
    """Checks if the local Ollama daemon is reachable and returns installed models."""
    tags_url = f"{base_url.rstrip('/')}/api/tags"
    try:
        req = urllib.request.Request(tags_url, headers={"User-Agent": "GeoMeasure-Setup/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                models = [m.get("name") for m in data.get("models", [])]
                return True, models, None
            return False, [], f"Unexpected HTTP status: {response.status}"
    except urllib.error.URLError as err:
        return False, [], f"Connection error: {err.reason}"
    except Exception as exc:
        return False, [], f"Error connecting to Ollama: {str(exc)}"


def pull_model(base_url: str, model_name: str):
    """Pulls the specified model via Ollama API with streaming progress."""
    pull_url = f"{base_url.rstrip('/')}/api/pull"
    payload = json.dumps({"name": model_name, "stream": True}).encode("utf-8")
    req = urllib.request.Request(
        pull_url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "GeoMeasure-Setup/1.0"},
        method="POST"
    )

    print(f"\n[INFO] Initiating pull for model '{model_name}' from Ollama registry...")
    print(f"[INFO] Reference: https://ollama.com/library/{model_name}")
    print("[INFO] Model weights will be stored in your Ollama directory, outside the git repo.\n")

    try:
        with urllib.request.urlopen(req, timeout=600) as response:
            last_status = ""
            for line in response:
                if not line:
                    continue
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    status = chunk.get("status", "")
                    completed = chunk.get("completed", 0)
                    total = chunk.get("total", 0)

                    if total > 0 and completed > 0:
                        pct = (completed / total) * 100
                        mb_done = completed / (1024 * 1024)
                        mb_total = total / (1024 * 1024)
                        sys.stdout.write(f"\r  {status}: {mb_done:.1f} MB / {mb_total:.1f} MB ({pct:.1f}%)   ")
                        sys.stdout.flush()
                    else:
                        if status != last_status:
                            print(f"  {status}")
                            last_status = status
                except json.JSONDecodeError:
                    continue
            print(f"\n\n[SUCCESS] Model '{model_name}' downloaded and ready for GeoMeasure Studio!")
            return True
    except Exception as exc:
        print(f"\n[ERROR] Failed to pull model '{model_name}': {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="GeoMeasure Studio Local Ollama Setup")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"Ollama base URL (default: {DEFAULT_BASE_URL})")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Target Ollama model (default: {DEFAULT_MODEL})")
    parser.add_argument("--check-only", action="store_true", help="Only verify connection without pulling")
    parser.add_argument("--pull", action="store_true", help="Automatically pull model if not installed")
    args = parser.parse_args()

    print("=" * 65)
    print(" GeoMeasure Studio v2 - Local AI Copilot Setup")
    print("=" * 65)
    print(f"Target Base URL : {args.base_url}")
    print(f"Target Model    : {args.model}")
    print("-" * 65)

    is_online, models, err_msg = check_ollama_status(args.base_url)

    if not is_online:
        print(f"[STATUS] OLLAMA OFFLINE / UNREACHABLE")
        print(f"Reason: {err_msg}\n")
        print("To install and run Ollama locally:")
        print("  1. Download Ollama from: https://ollama.com/download")
        print("  2. Start the Ollama application or daemon in your terminal:")
        print("     $ ollama serve")
        print("  3. Download the model manually if preferred:")
        print(f"     $ ollama pull {args.model}")
        print("  4. Re-run this check script:")
        print(f"     $ python scripts/setup_ollama.py --check-only")
        print("\nNote: GeoMeasure Studio runs safely even without Ollama. Fast deterministic")
        print("intents and hosted Groq inference remain fully operational.")
        sys.exit(1)

    print(f"[STATUS] OLLAMA ONLINE (Reachable at {args.base_url})")
    print(f"Installed models ({len(models)}): {', '.join(models) if models else 'None'}")

    model_installed = any(
        m == args.model or m.startswith(f"{args.model}:") or args.model.startswith(m)
        for m in models
    )

    if model_installed:
        print(f"\n[SUCCESS] Recommended model '{args.model}' is installed and ready to serve!")
        print("You can start GeoMeasure Studio with local inference enabled:")
        print("  AI_PROVIDER_MODE=local_first")
        print("  OLLAMA_BASE_URL=" + args.base_url)
        print("  OLLAMA_MODEL=" + args.model)
        sys.exit(0)

    print(f"\n[WARNING] Model '{args.model}' is not currently installed in Ollama.")

    if args.check_only:
        print(f"To pull it manually, run:")
        print(f"  $ ollama pull {args.model}")
        sys.exit(2)

    if args.pull:
        success = pull_model(args.base_url, args.model)
        sys.exit(0 if success else 1)
    else:
        print(f"Run this script with --pull to download it automatically:")
        print(f"  $ python scripts/setup_ollama.py --pull")
        print(f"Or via the Ollama CLI:")
        print(f"  $ ollama pull {args.model}")
        sys.exit(2)


if __name__ == "__main__":
    main()
