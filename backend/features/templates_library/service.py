from pathlib import Path

from pymongo import UpdateOne

from extensions import LIBRARY_DIR, templates_col
from shared.pptx_utils import get_slide_count
from shared.time_utils import utc_now


def scan_library() -> int:
    lib = Path(LIBRARY_DIR)
    if not lib.exists():
        return 0
    ops, now = [], utc_now()
    for f in lib.glob("*.pptx"):
        ops.append(UpdateOne(
            {"filename": f.name},
            {"$set": {"filename": f.name, "path": str(f), "size": f.stat().st_size,
                      "slide_count": get_slide_count(f), "updated_at": now},
             "$setOnInsert": {"created_at": now}},
            upsert=True,
        ))
    if ops:
        templates_col.bulk_write(ops)
    return len(ops)
