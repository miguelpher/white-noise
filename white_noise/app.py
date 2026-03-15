"""White Noise Player — FastAPI backend."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from jinja2 import Environment, FileSystemLoader

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
MUSIC_DIR = PROJECT_ROOT / "music_files"
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def load_config() -> dict:
    """Load the song mapping from config.json."""
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="White Noise Player")

jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=True,
)

# ---------------------------------------------------------------------------
# Playback state
# ---------------------------------------------------------------------------

_current_process: subprocess.Popen | None = None
_current_song: str | None = None


def _kill_current() -> None:
    """Terminate the currently playing mpg123 process, if any."""
    global _current_process, _current_song
    if _current_process is not None:
        try:
            _current_process.terminate()
            _current_process.wait(timeout=3)
        except ProcessLookupError:
            pass  # already exited
        except subprocess.TimeoutExpired:
            _current_process.kill()
        _current_process = None
        _current_song = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the player page."""
    config = load_config()
    template = jinja_env.get_template("index.html")
    html = template.render(songs=config["songs"])
    return HTMLResponse(content=html)


@app.post("/play/{song_key}")
async def play(song_key: str):
    """Start playing a song, stopping any currently playing one first."""
    global _current_process, _current_song

    config = load_config()
    songs = config["songs"]

    if song_key not in songs:
        raise HTTPException(status_code=404, detail=f"Unknown song key: {song_key}")

    file_path = MUSIC_DIR / songs[song_key]
    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Audio file not found: {file_path}. Update config.json with the correct path.",
        )

    # Stop whatever is currently playing
    _kill_current()

    # Start mpg123 in a subprocess
    try:
        _current_process = subprocess.Popen(
            ["mpg123", str(file_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="mpg123 is not installed. Install it with: sudo apt install mpg123",
        )
    _current_song = song_key

    return {"status": "playing", "song": song_key}


@app.post("/stop")
async def stop():
    """Stop the currently playing song."""
    _kill_current()
    return {"status": "stopped"}


@app.get("/status")
async def status():
    """Return the current playback status."""
    global _current_process, _current_song

    # Check if the process is still alive
    if _current_process is not None:
        retcode = _current_process.poll()
        if retcode is not None:
            # Process has finished on its own
            _current_process = None
            _current_song = None

    return {
        "playing": _current_song is not None,
        "song": _current_song,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """CLI entry point — start the uvicorn server."""
    import uvicorn

    uvicorn.run(
        "white_noise.app:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )


if __name__ == "__main__":
    main()
