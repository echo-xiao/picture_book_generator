"""Verify the app's MongoDB user has enough — and ideally not more than —
permission. Exercises every operation the app actually performs against the
configured database. If all steps pass, a `readWrite` role on
`picture_book_generator` is sufficient and the user can be tightened to that
(no atlasAdmin / readWriteAnyDatabase needed).

Run it BEFORE and AFTER changing the Atlas role to confirm nothing broke:
    python scripts/check_db_permissions.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pymongo  # noqa: E402

from src.config import MONGODB_URI, MONGODB_DB  # noqa: E402


def main() -> None:
    client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=10000)

    # The app pings on startup (src/core/db.py). ping needs no special grant.
    client.admin.command("ping")
    print("✓ ping (startup health check)")

    db = client[MONGODB_DB]
    coll = db["_perm_check"]
    try:
        coll.insert_one({"_id": "probe", "v": 1})
        print("✓ insert")
        assert coll.find_one({"_id": "probe"}) is not None
        print("✓ read")
        coll.update_one({"_id": "probe"}, {"$set": {"v": 2}})
        print("✓ update")
        coll.create_index("v")
        print("✓ create_index (used by the books-schema migration)")
        list(coll.aggregate([{"$match": {}}, {"$count": "n"}]))
        print("✓ aggregate (character-frequency analysis)")
        coll.delete_many({})
        print("✓ delete")
        coll.drop()
        print("✓ drop collection")
    finally:
        client.close()

    print("\nAll operations succeeded → `readWrite` on "
          f"`{MONGODB_DB}` is sufficient. You can safely tighten the user.")


if __name__ == "__main__":
    main()
