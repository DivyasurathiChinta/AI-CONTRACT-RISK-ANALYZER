"""
run.py
------
Convenience startup script for development.

USAGE:
    python run.py           → Start the FastAPI backend server
    python run.py --help    → Show all options

WHY A SEPARATE run.py:
- Allows passing custom host/port from command line
- Shows startup banner with useful information
- Single entry point that interviewers can understand quickly
"""

import argparse
import sys
import subprocess
from pathlib import Path


def print_banner():
    banner = """
╔══════════════════════════════════════════════════════════════╗
║          🤖  AI CONTRACT RISK ANALYZER  v1.0.0              ║
║          Powered by Google Gemini AI + FastAPI              ║
╚══════════════════════════════════════════════════════════════╝

  Backend API  →  http://localhost:8000
  API Docs     →  http://localhost:8000/docs
  Health Check →  http://localhost:8000/health

  To start the Streamlit frontend (in a new terminal):
    streamlit run frontend/streamlit_app.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(banner)


def check_env():
    """Verify .env file and critical settings exist."""
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  WARNING: .env file not found!")
        print("   Copy .env.example to .env and add your GEMINI_API_KEY")
        print("   Command: copy .env.example .env")
        print()
    else:
        # Check for placeholder API key
        content = env_file.read_text()
        if "your_gemini_api_key_here" in content or "GEMINI_API_KEY=" not in content:
            print("⚠️  WARNING: GEMINI_API_KEY not configured in .env")
            print("   Get your key at: https://aistudio.google.com/app/apikey")
            print()


def check_uploads_dir():
    """Ensure uploads directory exists."""
    uploads = Path("uploads")
    uploads.mkdir(exist_ok=True)


def start_backend(host: str = "0.0.0.0", port: int = 8000, reload: bool = True):
    """Start the FastAPI backend using uvicorn."""
    print_banner()
    check_env()
    check_uploads_dir()

    cmd = [
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", host,
        "--port", str(port),
    ]
    if reload:
        cmd.append("--reload")

    print(f"🚀 Starting backend on http://{host}:{port}")
    print("   Press CTRL+C to stop\n")

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\n\n✅ Server stopped gracefully.")
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="AI Contract Risk Analyzer - Development Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                        # Default: host=0.0.0.0, port=8000
  python run.py --port 9000            # Custom port
  python run.py --no-reload            # Disable auto-reload (production-like)
        """
    )
    parser.add_argument("--host", default="0.0.0.0", help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8000, help="Port number (default: 8000)")
    parser.add_argument("--no-reload", action="store_true", help="Disable auto-reload")

    args = parser.parse_args()
    start_backend(host=args.host, port=args.port, reload=not args.no_reload)
