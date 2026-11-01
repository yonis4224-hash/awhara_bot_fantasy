"""
Cloud Storage Sync Engine via GitHub Gist (cloud_sync.py)
Automatically pulls the latest activity and shop data on bot boot,
and pushes incremental backups periodically in the background so data is never lost across Render restarts.
"""
import os
import json
import logging
import asyncio
import urllib.request
import urllib.error

log = logging.getLogger("cloud_sync")

GIST_ID = os.getenv("GIST_ID", "75cc16928c4786055acf4cfcf4ff656b")
GIST_TOKEN = os.getenv("GIST_TOKEN", "")

LOCAL_FILES = {
    "activity_data.json": os.path.join("src", "data", "activity_data.json"),
    "roulette_shop.json": os.path.join("src", "data", "roulette_shop.json")
}

_pending_save = False


def pull_from_gist():
    """Download latest cloud state on startup and save to local disk."""
    if not GIST_ID or not GIST_TOKEN:
        log.warning("GIST_ID or GIST_TOKEN missing, running on local files only.")
        return False

    try:
        url = f"https://api.github.com/gists/{GIST_ID}"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"token {GIST_TOKEN}",
                "User-Agent": "AwharaBot-CloudSync",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            files = data.get("files", {})

            for filename, path in LOCAL_FILES.items():
                if filename in files:
                    content = files[filename].get("content")
                    if content:
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        with open(path, "w", encoding="utf-8") as f:
                            f.write(content)
                        log.info(f"✅ Synced {filename} from cloud Gist.")
            return True
    except Exception as e:
        log.error(f"❌ Failed to pull data from Gist: {e}")
        return False


def push_to_gist_sync():
    """Uploads current local JSON files to the secret Gist."""
    if not GIST_ID or not GIST_TOKEN:
        return False

    files_payload = {}
    for filename, path in LOCAL_FILES.items():
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    if content.strip():
                        files_payload[filename] = {"content": content}
            except Exception as e:
                log.error(f"Could not read {path} for gist upload: {e}")

    if not files_payload:
        return False

    try:
        url = f"https://api.github.com/gists/{GIST_ID}"
        body = json.dumps({"files": files_payload}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"token {GIST_TOKEN}",
                "User-Agent": "AwharaBot-CloudSync",
                "Content-Type": "application/json",
                "Accept": "application/vnd.github.v3+json"
            },
            method="PATCH"
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info("☁️ Successfully backed up activity and points to cloud Gist.")
            return True
    except Exception as e:
        log.error(f"❌ Failed to backup to Gist: {e}")
        return False


def request_cloud_backup():
    """Triggered by activity or shop changes to schedule a cloud backup."""
    global _pending_save
    _pending_save = True


async def cloud_sync_background_loop():
    """Runs continuously in the background, flushing dirty states every 30 seconds."""
    global _pending_save
    while True:
        try:
            await asyncio.sleep(30)
            if _pending_save:
                _pending_save = False
                await asyncio.to_thread(push_to_gist_sync)
        except asyncio.CancelledError:
            break
        except Exception as e:
            log.error(f"Error in cloud sync loop: {e}")
