import os
from fastapi import HTTPException

LOCK_FILE = "/tmp/tokenpost_batch.lock"

def acquire_lock():
    if os.path.exists(LOCK_FILE):
        raise HTTPException(400, "Batch is already running")
    open(LOCK_FILE, "w").close()

def release_lock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)