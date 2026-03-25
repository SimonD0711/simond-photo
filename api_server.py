#!/usr/bin/env python3
import base64
import hashlib
import hmac
import json
import os
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen


BASE_DIR = Path("/var/www/html")
DB_PATH = BASE_DIR / "engagement.db"
UNKNOWN_LOCATION = "\u672a\u77e5\u4f4d\u7f6e"
ADMIN_NAME = "SimonD\uff08\u7ad9\u4e3b\uff09"
ADMIN_PASSWORD_SALT_B64 = "0vNdaJp6H0CvTbdDuJ3aPA=="
ADMIN_PASSWORD_HASH_B64 = "azlZ+ZCaO0JOHsIIVYkhKfuLxUIACLDWwxiaI3+5ZJI="
ADMIN_SESSION_SECRET = "2c80b1f822a936df1d2fe5089abfca25d33964f81059b7f69991873efd35dd99"
ADMIN_SESSION_COOKIE = "cc_admin_session"
ADMIN_SESSION_TTL = 60 * 60 * 24 * 30


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS photo_likes (
            photo_id TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (photo_id, ip_address)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS photo_comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            photo_id TEXT NOT NULL,
            parent_id INTEGER,
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            is_pinned INTEGER NOT NULL DEFAULT 0,
            is_owner INTEGER NOT NULL DEFAULT 0,
            ip_address TEXT NOT NULL,
            masked_ip TEXT NOT NULL,
            location_label TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS comment_likes (
            comment_id INTEGER NOT NULL,
            ip_address TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (comment_id, ip_address)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ip_geo_cache (
            ip_address TEXT PRIMARY KEY,
            location_label TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(photo_comments)").fetchall()}
    if "location_label" not in columns:
        conn.execute("ALTER TABLE photo_comments ADD COLUMN location_label TEXT NOT NULL DEFAULT ''")
    if "parent_id" not in columns:
        conn.execute("ALTER TABLE photo_comments ADD COLUMN parent_id INTEGER")
    if "is_pinned" not in columns:
        conn.execute("ALTER TABLE photo_comments ADD COLUMN is_pinned INTEGER NOT NULL DEFAULT 0")
    if "is_owner" not in columns:
        conn.execute("ALTER TABLE photo_comments ADD COLUMN is_owner INTEGER NOT NULL DEFAULT 0")
    return conn


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def mask_ip(ip):
    if ":" in ip:
        parts = ip.split(":")
        if len(parts) >= 4:
            return ":".join(parts[:2] + ["****", "****"])
        return ip
    parts = ip.split(".")
    if len(parts) == 4:
        return ".".join(parts[:2] + ["*", "*"])
    return ip


def normalize_ip(handler):
    forwarded = handler.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return handler.client_address[0]


def parse_cookies(handler):
    cookie_header = handler.headers.get("Cookie", "")
    cookies = {}
    for item in cookie_header.split(";"):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        cookies[key.strip()] = value.strip()
    return cookies


def sign_admin_session(expires_at):
    message = f"admin|{expires_at}".encode("utf-8")
    return hmac.new(ADMIN_SESSION_SECRET.encode("utf-8"), message, hashlib.sha256).hexdigest()


def make_admin_session_cookie():
    expires_at = int(time.time()) + ADMIN_SESSION_TTL
    signature = sign_admin_session(expires_at)
    token = base64.urlsafe_b64encode(f"{expires_at}:{signature}".encode("utf-8")).decode("ascii")
    return f"{ADMIN_SESSION_COOKIE}={token}; Max-Age={ADMIN_SESSION_TTL}; Path=/; HttpOnly; SameSite=Lax"


def clear_admin_session_cookie():
    return f"{ADMIN_SESSION_COOKIE}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax"


def is_admin_authenticated(handler):
    token = parse_cookies(handler).get(ADMIN_SESSION_COOKIE)
    if not token:
        return False
    try:
        decoded = base64.urlsafe_b64decode(token.encode("ascii")).decode("utf-8")
        expires_at_raw, signature = decoded.split(":", 1)
        expires_at = int(expires_at_raw)
    except Exception:
        return False
    if expires_at < int(time.time()):
        return False
    return hmac.compare_digest(signature, sign_admin_session(expires_at))


def verify_admin_password(password):
    salt = base64.b64decode(ADMIN_PASSWORD_SALT_B64)
    expected = base64.b64decode(ADMIN_PASSWORD_HASH_B64)
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210000, dklen=32)
    return hmac.compare_digest(actual, expected)


def get_location_label(conn, ip):
    if not ip:
        return UNKNOWN_LOCATION

    cached = conn.execute(
        "SELECT location_label FROM ip_geo_cache WHERE ip_address = ?",
        (ip,),
    ).fetchone()
    if cached:
        return cached["location_label"]

    try:
        with urlopen(
            f"http://ip-api.com/json/{ip}?fields=status,country,regionName,city&lang=zh-CN",
            timeout=4,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("status") == "success":
            pieces = [payload.get("country"), payload.get("regionName"), payload.get("city")]
            label = " ".join([item.strip() for item in pieces if item and item.strip()]) or UNKNOWN_LOCATION
        else:
            label = UNKNOWN_LOCATION
    except Exception:
        label = UNKNOWN_LOCATION

    conn.execute(
        "INSERT OR REPLACE INTO ip_geo_cache (ip_address, location_label, updated_at) VALUES (?, ?, ?)",
        (ip, label, utc_now()),
    )
    conn.commit()
    return label


def is_mainland_china_label(label):
    return bool(label and label.startswith("中国"))


def fetch_comment_rows(conn, viewer_ip, viewer_is_admin, photo_id=None):
    query = """
        SELECT id, photo_id, parent_id, author, body, is_pinned, is_owner, masked_ip, created_at,
               location_label,
               COALESCE(cl.like_count, 0) AS like_count,
               CASE WHEN ul.comment_id IS NOT NULL THEN 1 ELSE 0 END AS liked,
               CASE WHEN ip_address = ? OR (is_owner = 1 AND ? = 1) THEN 1 ELSE 0 END AS can_edit,
               CASE WHEN ip_address = ? OR ? = 1 THEN 1 ELSE 0 END AS can_delete,
               CASE WHEN ? = 1 THEN 1 ELSE 0 END AS can_pin
        FROM photo_comments
        LEFT JOIN (
            SELECT comment_id, COUNT(*) AS like_count
            FROM comment_likes
            GROUP BY comment_id
        ) AS cl ON cl.comment_id = photo_comments.id
        LEFT JOIN (
            SELECT comment_id
            FROM comment_likes
            WHERE ip_address = ?
        ) AS ul ON ul.comment_id = photo_comments.id
    """
    params = [
        viewer_ip,
        1 if viewer_is_admin else 0,
        viewer_ip,
        1 if viewer_is_admin else 0,
        1 if viewer_is_admin else 0,
        viewer_ip,
    ]
    if photo_id:
        query += " WHERE photo_id = ?"
        params.append(photo_id)
    query += " ORDER BY id ASC"
    return conn.execute(query, params).fetchall()


def fetch_like_insights(conn, photo_id):
    rows = conn.execute(
        """
        SELECT ip_address, created_at
        FROM photo_likes
        WHERE photo_id = ?
        ORDER BY created_at DESC
        """,
        (photo_id,),
    ).fetchall()
    insights = []
    for row in rows:
        ip_address = row["ip_address"]
        insights.append(
            {
                "masked_ip": mask_ip(ip_address),
                "location_label": get_location_label(conn, ip_address),
                "created_at": row["created_at"],
            }
        )
    return {"count": len(insights), "likes": insights}


def fetch_admin_stats(conn):
    summary = conn.execute(
        """
        SELECT
            (SELECT COUNT(*) FROM photo_likes) AS total_likes,
            (SELECT COUNT(*) FROM photo_comments) AS total_comments,
            (SELECT COUNT(DISTINCT photo_id) FROM photo_likes) AS liked_photos,
            (SELECT COUNT(DISTINCT photo_id) FROM photo_comments) AS commented_photos
        """
    ).fetchone()

    photo_rows = conn.execute(
        """
        SELECT
            p.photo_id,
            COALESCE(l.like_count, 0) AS likes,
            COALESCE(c.comment_count, 0) AS comments,
            COALESCE(c.owner_comment_count, 0) AS owner_comments,
            COALESCE(c.last_comment_at, '') AS last_comment_at
        FROM (
            SELECT photo_id FROM photo_likes
            UNION
            SELECT photo_id FROM photo_comments
        ) AS p
        LEFT JOIN (
            SELECT photo_id, COUNT(*) AS like_count
            FROM photo_likes
            GROUP BY photo_id
        ) AS l ON l.photo_id = p.photo_id
        LEFT JOIN (
            SELECT
                photo_id,
                COUNT(*) AS comment_count,
                SUM(CASE WHEN is_owner = 1 THEN 1 ELSE 0 END) AS owner_comment_count,
                MAX(created_at) AS last_comment_at
            FROM photo_comments
            GROUP BY photo_id
        ) AS c ON c.photo_id = p.photo_id
        ORDER BY likes DESC, comments DESC, p.photo_id ASC
        """
    ).fetchall()

    like_location_rows = conn.execute(
        """
        SELECT ip_address
        FROM photo_likes
        ORDER BY created_at DESC
        """
    ).fetchall()
    like_location_counts = {}
    for row in like_location_rows:
        label = get_location_label(conn, row["ip_address"])
        like_location_counts[label] = like_location_counts.get(label, 0) + 1

    comment_location_rows = conn.execute(
        """
        SELECT location_label, COUNT(*) AS count
        FROM photo_comments
        GROUP BY location_label
        ORDER BY count DESC, location_label ASC
        """
    ).fetchall()

    return {
        "summary": {
            "total_likes": summary["total_likes"],
            "total_comments": summary["total_comments"],
            "liked_photos": summary["liked_photos"],
            "commented_photos": summary["commented_photos"],
        },
        "photos": [dict(row) for row in photo_rows],
        "like_locations": [
            {"location_label": label, "count": count}
            for label, count in sorted(like_location_counts.items(), key=lambda item: (-item[1], item[0]))
        ],
        "comment_locations": [dict(row) for row in comment_location_rows],
    }


def format_uptime(total_seconds):
    total_seconds = max(int(total_seconds), 0)
    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    if days:
        return f"{days}d {hours}h {minutes}m"
    if hours:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def read_meminfo():
    meminfo = {}
    try:
        with open("/proc/meminfo", "r", encoding="utf-8") as handle:
            for line in handle:
                key, value = line.split(":", 1)
                meminfo[key] = int(value.strip().split()[0])
    except Exception:
        return {}
    return meminfo


def read_cpu_times():
    try:
        with open("/proc/stat", "r", encoding="utf-8") as handle:
            line = handle.readline()
    except Exception:
        return None
    parts = line.split()
    if not parts or parts[0] != "cpu":
        return None
    values = [int(item) for item in parts[1:]]
    total = sum(values)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return total, idle


def sample_cpu_percent(delay=0.12):
    first = read_cpu_times()
    if not first:
        return None
    time.sleep(delay)
    second = read_cpu_times()
    if not second:
        return None
    total_delta = second[0] - first[0]
    idle_delta = second[1] - first[1]
    if total_delta <= 0:
        return None
    return round(max(0.0, min(100.0, (1 - idle_delta / total_delta) * 100)), 1)


def service_status(name):
    try:
        result = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return (result.stdout or result.stderr).strip() or "unknown"
    except Exception:
        return "unknown"


def fetch_server_status():
    meminfo = read_meminfo()
    total_mem_kb = meminfo.get("MemTotal", 0)
    available_mem_kb = meminfo.get("MemAvailable", 0)
    swap_total_kb = meminfo.get("SwapTotal", 0)
    swap_free_kb = meminfo.get("SwapFree", 0)
    disk_total, disk_used, disk_free = shutil.disk_usage("/")
    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        load1 = load5 = load15 = 0.0
    cpu_percent = sample_cpu_percent()
    uptime_seconds = 0.0
    try:
        with open("/proc/uptime", "r", encoding="utf-8") as handle:
            uptime_seconds = float(handle.read().split()[0])
    except Exception:
        uptime_seconds = 0.0

    return {
        "checked_at": utc_now(),
        "hostname": os.uname().nodename,
        "uptime": format_uptime(uptime_seconds),
        "cpu": {
            "usage_percent": cpu_percent,
            "load_average": [round(load1, 2), round(load5, 2), round(load15, 2)],
            "cores": os.cpu_count() or 1,
        },
        "memory": {
            "total_mb": round(total_mem_kb / 1024, 1),
            "available_mb": round(available_mem_kb / 1024, 1),
            "used_mb": round(max(total_mem_kb - available_mem_kb, 0) / 1024, 1),
            "usage_percent": round(((total_mem_kb - available_mem_kb) / total_mem_kb) * 100, 1) if total_mem_kb else None,
        },
        "swap": {
            "total_mb": round(swap_total_kb / 1024, 1),
            "used_mb": round(max(swap_total_kb - swap_free_kb, 0) / 1024, 1),
            "usage_percent": round(((swap_total_kb - swap_free_kb) / swap_total_kb) * 100, 1) if swap_total_kb else 0.0,
        },
        "disk": {
            "total_gb": round(disk_total / (1024 ** 3), 1),
            "used_gb": round(disk_used / (1024 ** 3), 1),
            "free_gb": round(disk_free / (1024 ** 3), 1),
            "usage_percent": round((disk_used / disk_total) * 100, 1) if disk_total else None,
        },
        "services": [
            {"name": "nginx", "status": service_status("nginx")},
            {"name": "cheungchau-api", "status": service_status("cheungchau-api")},
        ],
    }


def shape_photo_comments(rows):
    comment_lookup = {}
    top_level = []

    for row in rows:
        comment = dict(row)
        comment.update({"replies": [], "reply_count": 0})
        comment_lookup[comment["id"]] = comment

    floor = 0
    for row in rows:
        comment = comment_lookup[row["id"]]
        parent_id = comment["parent_id"]
        if parent_id is None:
            floor += 1
            comment["floor"] = floor
            top_level.append(comment)
            continue
        parent = comment_lookup.get(parent_id)
        if not parent:
            floor += 1
            comment["floor"] = floor
            top_level.append(comment)
            continue
        comment["floor"] = parent["floor"]
        comment["reply_to_author"] = parent["author"]
        parent["replies"].append(comment)

    def finalize(nodes):
        total = 0
        for node in nodes:
            node["replies"].sort(key=lambda item: (0 if item["is_pinned"] else 1, item["id"]))
            total += 1
            total += finalize(node["replies"])
            node["reply_count"] = len(node["replies"])
        return total

    top_level.sort(key=lambda item: (0 if item["is_pinned"] else 1, item["id"]))
    total_comments = finalize(top_level)
    return {"comments": top_level, "comment_count": total_comments}


def photo_payload(conn, photo_id, viewer_ip="", viewer_is_admin=False):
    likes = conn.execute(
        "SELECT COUNT(*) AS count FROM photo_likes WHERE photo_id = ?",
        (photo_id,),
    ).fetchone()["count"]
    comments_payload = shape_photo_comments(fetch_comment_rows(conn, viewer_ip, viewer_is_admin, photo_id))
    return {
        "likes": likes,
        "comments": comments_payload["comments"],
        "comment_count": comments_payload["comment_count"],
        "admin_authenticated": viewer_is_admin,
    }


def photo_payloads(conn, viewer_ip="", viewer_is_admin=False):
    payload = {}

    for row in conn.execute(
        "SELECT photo_id, COUNT(*) AS count FROM photo_likes GROUP BY photo_id"
    ).fetchall():
        payload[row["photo_id"]] = {
            "likes": row["count"],
            "comments": [],
            "comment_count": 0,
            "admin_authenticated": viewer_is_admin,
        }

    comment_rows = fetch_comment_rows(conn, viewer_ip, viewer_is_admin)
    grouped = {}
    for row in comment_rows:
        grouped.setdefault(row["photo_id"], []).append(row)

    for photo_id, rows in grouped.items():
        entry = payload.setdefault(
            photo_id,
            {"likes": 0, "comments": [], "comment_count": 0, "admin_authenticated": viewer_is_admin},
        )
        comments_payload = shape_photo_comments(rows)
        entry["comments"] = comments_payload["comments"]
        entry["comment_count"] = comments_payload["comment_count"]

    return payload


def collect_descendant_ids(conn, root_id):
    pending = [root_id]
    descendants = []
    while pending:
        current_id = pending.pop()
        children = conn.execute(
            "SELECT id FROM photo_comments WHERE parent_id = ?",
            (current_id,),
        ).fetchall()
        child_ids = [row["id"] for row in children]
        descendants.extend(child_ids)
        pending.extend(child_ids)
    return descendants


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200, extra_headers=None):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if extra_headers:
            for header_name, header_value in extra_headers:
                self.send_header(header_name, header_value)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self._send_json({}, 204)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/map-tile/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 5 and parts[0] == "api" and parts[1] == "map-tile" and parts[4].endswith(".png"):
                z = parts[2]
                x = parts[3]
                y = parts[4][:-4]
            elif len(parts) == 5 and parts[0] == "api" and parts[1] == "map-tile":
                z = parts[2]
                x = parts[3]
                y = parts[4]
            else:
                self.send_error(404)
                return
            tile_url = f"https://tile.openstreetmap.org/{z}/{x}/{y}.png"
            try:
                request = Request(tile_url, headers={"User-Agent": "simond.photo-map-proxy/1.0"})
                with urlopen(request, timeout=8) as response:
                    body = response.read()
                    content_type = response.headers.get("Content-Type", "image/png")
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "public, max-age=86400")
                self.end_headers()
                self.wfile.write(body)
            except Exception:
                self.send_error(502)
            return

        if parsed.path == "/api/client-context":
            conn = get_db()
            try:
                ip = normalize_ip(self)
                location_label = get_location_label(conn, ip)
                self._send_json(
                    {
                        "location_label": location_label,
                        "is_mainland_china": is_mainland_china_label(location_label),
                    }
                )
            finally:
                conn.close()
            return

        if parsed.path == "/api/engagement":
            conn = get_db()
            try:
                ip = normalize_ip(self)
                viewer_is_admin = is_admin_authenticated(self)
                qs = parse_qs(parsed.query)
                photo_id = qs.get("photo_id", [""])[0].strip()
                if not photo_id:
                    self._send_json(photo_payloads(conn, ip, viewer_is_admin))
                    return
                self._send_json(photo_payload(conn, photo_id, ip, viewer_is_admin))
            finally:
                conn.close()
            return

        if parsed.path == "/api/admin/status":
            self._send_json({"authenticated": is_admin_authenticated(self), "display_name": ADMIN_NAME})
            return

        if parsed.path == "/api/admin/likes":
            if not is_admin_authenticated(self):
                self._send_json({"error": "Forbidden"}, 403)
                return
            conn = get_db()
            try:
                qs = parse_qs(parsed.query)
                photo_id = qs.get("photo_id", [""])[0].strip()
                if not photo_id:
                    self._send_json({"error": "Missing photo_id"}, 400)
                    return
                self._send_json(fetch_like_insights(conn, photo_id))
            finally:
                conn.close()
            return

        if parsed.path == "/api/admin/stats":
            if not is_admin_authenticated(self):
                self._send_json({"error": "Forbidden"}, 403)
                return
            conn = get_db()
            try:
                self._send_json(fetch_admin_stats(conn))
            finally:
                conn.close()
            return

        if parsed.path == "/api/admin/server-status":
            if not is_admin_authenticated(self):
                self._send_json({"error": "Forbidden"}, 403)
                return
            self._send_json(fetch_server_status())
            return

        self._send_json({"error": "Not found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            data = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON"}, 400)
            return

        if parsed.path == "/api/admin/login":
            password = str(data.get("password", ""))
            if not verify_admin_password(password):
                self._send_json({"error": "Invalid password"}, 403)
                return
            self._send_json(
                {"authenticated": True, "display_name": ADMIN_NAME},
                extra_headers=[("Set-Cookie", make_admin_session_cookie())],
            )
            return

        if parsed.path == "/api/admin/logout":
            self._send_json(
                {"authenticated": False},
                extra_headers=[("Set-Cookie", clear_admin_session_cookie())],
            )
            return

        conn = get_db()
        ip = normalize_ip(self)
        viewer_is_admin = is_admin_authenticated(self)
        now = utc_now()
        try:
            if parsed.path == "/api/like":
                photo_id = str(data.get("photo_id", "")).strip()
                if not photo_id:
                    self._send_json({"error": "Missing photo_id"}, 400)
                    return
                existing = conn.execute(
                    "SELECT 1 FROM photo_likes WHERE photo_id = ? AND ip_address = ?",
                    (photo_id, ip),
                ).fetchone()
                if existing:
                    conn.execute(
                        "DELETE FROM photo_likes WHERE photo_id = ? AND ip_address = ?",
                        (photo_id, ip),
                    )
                    liked = False
                else:
                    conn.execute(
                        "INSERT INTO photo_likes (photo_id, ip_address, created_at) VALUES (?, ?, ?)",
                        (photo_id, ip, now),
                    )
                    get_location_label(conn, ip)
                    liked = True
                conn.commit()
                payload = photo_payload(conn, photo_id, ip, viewer_is_admin)
                payload["liked"] = liked
                self._send_json(payload)
                return

            if parsed.path == "/api/comment":
                photo_id = str(data.get("photo_id", "")).strip()
                author = str(data.get("author", "")).strip()[:40]
                body = str(data.get("body", "")).strip()[:500]
                parent_id = int(data.get("parent_id", 0) or 0) or None
                if viewer_is_admin:
                    author = ADMIN_NAME
                if not photo_id or not author or not body:
                    self._send_json({"error": "Missing fields"}, 400)
                    return
                if parent_id is not None:
                    parent = conn.execute(
                        "SELECT id FROM photo_comments WHERE id = ? AND photo_id = ?",
                        (parent_id, photo_id),
                    ).fetchone()
                    if not parent:
                        self._send_json({"error": "Parent comment not found"}, 400)
                        return
                conn.execute(
                    """
                    INSERT INTO photo_comments (
                        photo_id, parent_id, author, body, is_owner, ip_address, masked_ip, location_label, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        photo_id,
                        parent_id,
                        author,
                        body,
                        1 if viewer_is_admin else 0,
                        ip,
                        mask_ip(ip),
                        get_location_label(conn, ip),
                        now,
                    ),
                )
                conn.commit()
                self._send_json(photo_payload(conn, photo_id, ip, viewer_is_admin))
                return

            if parsed.path == "/api/comment/like":
                comment_id = int(data.get("comment_id", 0) or 0)
                if not comment_id:
                    self._send_json({"error": "Missing comment_id"}, 400)
                    return
                row = conn.execute(
                    "SELECT photo_id FROM photo_comments WHERE id = ?",
                    (comment_id,),
                ).fetchone()
                if not row:
                    self._send_json({"error": "Comment not found"}, 404)
                    return
                existing = conn.execute(
                    "SELECT 1 FROM comment_likes WHERE comment_id = ? AND ip_address = ?",
                    (comment_id, ip),
                ).fetchone()
                if existing:
                    conn.execute(
                        "DELETE FROM comment_likes WHERE comment_id = ? AND ip_address = ?",
                        (comment_id, ip),
                    )
                else:
                    conn.execute(
                        "INSERT INTO comment_likes (comment_id, ip_address, created_at) VALUES (?, ?, ?)",
                        (comment_id, ip, now),
                    )
                conn.commit()
                self._send_json(photo_payload(conn, row["photo_id"], ip, viewer_is_admin))
                return

            if parsed.path == "/api/comment/pin":
                comment_id = int(data.get("comment_id", 0) or 0)
                pinned = 1 if data.get("pinned") else 0
                if not viewer_is_admin or not comment_id:
                    self._send_json({"error": "Forbidden"}, 403)
                    return
                row = conn.execute(
                    "SELECT photo_id FROM photo_comments WHERE id = ?",
                    (comment_id,),
                ).fetchone()
                if not row:
                    self._send_json({"error": "Comment not found"}, 404)
                    return
                conn.execute(
                    "UPDATE photo_comments SET is_pinned = ? WHERE id = ?",
                    (pinned, comment_id),
                )
                conn.commit()
                self._send_json(photo_payload(conn, row["photo_id"], ip, viewer_is_admin))
                return

            if parsed.path == "/api/comment/update":
                photo_id = str(data.get("photo_id", "")).strip()
                author = str(data.get("author", "")).strip()[:40]
                body = str(data.get("body", "")).strip()[:500]
                comment_id = int(data.get("comment_id", 0) or 0)
                if viewer_is_admin:
                    author = ADMIN_NAME
                if not photo_id or not author or not body or not comment_id:
                    self._send_json({"error": "Missing fields"}, 400)
                    return
                row = conn.execute(
                    """
                    SELECT id FROM photo_comments
                    WHERE id = ? AND photo_id = ? AND (ip_address = ? OR (is_owner = 1 AND ? = 1))
                    """,
                    (comment_id, photo_id, ip, 1 if viewer_is_admin else 0),
                ).fetchone()
                if not row:
                    self._send_json({"error": "Forbidden"}, 403)
                    return
                conn.execute(
                    "UPDATE photo_comments SET author = ?, body = ? WHERE id = ?",
                    (author, body, comment_id),
                )
                conn.commit()
                self._send_json(photo_payload(conn, photo_id, ip, viewer_is_admin))
                return

            if parsed.path == "/api/comment/delete":
                comment_id = int(data.get("comment_id", 0) or 0)
                if not comment_id:
                    self._send_json({"error": "Missing comment_id"}, 400)
                    return
                row = conn.execute(
                    """
                    SELECT photo_id, parent_id FROM photo_comments
                    WHERE id = ? AND (ip_address = ? OR ? = 1)
                    """,
                    (comment_id, ip, 1 if viewer_is_admin else 0),
                ).fetchone()
                if not row:
                    self._send_json({"error": "Forbidden"}, 403)
                    return
                photo_id = row["photo_id"]
                parent_id = row["parent_id"]
                if parent_id is None:
                    descendant_ids = collect_descendant_ids(conn, comment_id)
                    placeholders = ", ".join(["?"] * (len(descendant_ids) + 1))
                    ids_to_delete = [comment_id] + descendant_ids
                    conn.execute(
                        f"DELETE FROM comment_likes WHERE comment_id IN ({placeholders})",
                        ids_to_delete,
                    )
                    conn.execute(
                        f"DELETE FROM photo_comments WHERE id IN ({placeholders})",
                        ids_to_delete,
                    )
                else:
                    conn.execute(
                        "DELETE FROM comment_likes WHERE comment_id = ?",
                        (comment_id,),
                    )
                    conn.execute(
                        "DELETE FROM photo_comments WHERE id = ?",
                        (comment_id,),
                    )
                conn.commit()
                self._send_json(photo_payload(conn, photo_id, ip, viewer_is_admin))
                return

            self._send_json({"error": "Not found"}, 404)
        finally:
            conn.close()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 9000), Handler)
    server.serve_forever()
