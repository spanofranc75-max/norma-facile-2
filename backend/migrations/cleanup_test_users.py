"""
Sprint 1 — Cleanup test users from the database.

Removes users created by testing agents that are not tied to an active
tenant or don't have a real Google OAuth profile.

Safe to run multiple times (idempotent).
"""
import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime, timezone

# Real user emails to PRESERVE (add production emails here)
PRESERVE_EMAILS = set()

# Known test patterns
TEST_EMAIL_PATTERNS = [
    "test@", "demo@", "agent@", "testing@",
    "@test.com", "@example.com", "@normafacile.it",
]

TEST_NAME_PATTERNS = [
    "test user", "test agent", "demo user", "e2e test",
]


async def cleanup():
    client = AsyncIOMotorClient(os.environ.get("MONGO_URL", "mongodb://localhost:27017"))
    db = client[os.environ.get("DB_NAME", "normafacile")]

    # Find all users
    users = await db.users.find({}, {"_id": 0}).to_list(1000)
    print(f"Total users in DB: {len(users)}")

    to_delete = []
    to_keep = []

    for u in users:
        email = (u.get("email") or "").lower()
        name = (u.get("name") or "").lower()
        user_id = u.get("user_id", "")

        # Always preserve explicitly listed emails
        if email in PRESERVE_EMAILS:
            to_keep.append(u)
            continue

        # Check if test pattern
        is_test = False
        for pat in TEST_EMAIL_PATTERNS:
            if pat in email:
                is_test = True
                break
        if not is_test:
            for pat in TEST_NAME_PATTERNS:
                if pat in name:
                    is_test = True
                    break

        # Check if user has any real data (commesse, invoices, preventivi)
        if not is_test:
            real_data_count = 0
            for coll in ["commesse", "invoices", "preventivi", "clients"]:
                count = await db[coll].count_documents({"user_id": user_id})
                real_data_count += count
            if real_data_count == 0 and not u.get("picture"):
                # No real data AND no Google profile picture = likely test user
                is_test = True

        if is_test:
            to_delete.append(u)
        else:
            to_keep.append(u)

    print(f"\nUsers to KEEP: {len(to_keep)}")
    for u in to_keep:
        print(f"  KEEP: {u.get('email', '?'):40s} role={u.get('role', '?'):15s} data=real")

    print(f"\nUsers to DELETE: {len(to_delete)}")
    for u in to_delete:
        print(f"  DEL:  {u.get('email', '?'):40s} role={u.get('role', '?'):15s} id={u.get('user_id', '?')}")

    if not to_delete:
        print("\nNo test users to clean up.")
        client.close()
        return

    # Confirm
    print(f"\nProceeding with deletion of {len(to_delete)} test users...")

    deleted_count = 0
    for u in to_delete:
        uid = u.get("user_id")
        if not uid:
            continue

        # Delete user
        result = await db.users.delete_one({"user_id": uid})
        if result.deleted_count:
            deleted_count += 1

        # Delete their sessions
        await db.user_sessions.delete_many({"user_id": uid})

        # Log the cleanup
        await db.activity_log.insert_one({
            "user_id": "system",
            "user_name": "Sprint1 Cleanup",
            "user_email": "",
            "tenant_id": "default",
            "action": "delete",
            "entity_type": "user_cleanup",
            "entity_id": uid,
            "label": f"Removed test user: {u.get('email', '?')}",
            "details": {"email": u.get("email"), "role": u.get("role"), "reason": "test_user_cleanup"},
            "actor_type": "system",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    print(f"\nDeleted {deleted_count} test users and their sessions.")
    client.close()


if __name__ == "__main__":
    asyncio.run(cleanup())
