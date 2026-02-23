import os
import uvicorn

if __name__ == "__main__":
    reload = os.environ.get("SUBTITLE_SYNC_DEV", "1") == "1"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8765, reload=reload)
