import json
import os

MEMBER_DIR = "backend/members/users"

def load_member(user_id):
    filepath = os.path.join(MEMBER_DIR, f"{user_id}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return None

def save_member(user_id, data):
    os.makedirs(MEMBER_DIR, exist_ok=True)
    filepath = os.path.join(MEMBER_DIR, f"{user_id}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_base_static_url():
    url = os.getenv("BASE_STATIC_URL", "https://your-default-url.com/static/")
    if not url.endswith("/"):
        url += "/"
    return url
