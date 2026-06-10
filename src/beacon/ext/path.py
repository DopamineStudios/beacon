from pathlib import Path
import importlib.resources

BASE_PATH = Path(__file__).parent

try:
    # Attempting to load as a package resource
    with importlib.resources.path("beacon.ext", "Bold.ttf") as p:
        BOLDFONT_PATH = str(p)
except Exception:
    # Fallback: Look for Bold.ttf in the same folder as this script
    BOLDFONT_PATH = str(BASE_PATH / "Bold.ttf")

framework_version = "3.2.5"
