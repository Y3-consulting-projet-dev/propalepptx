import os
import base64
import glob
import time
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient, UpdateOne
from pptx import Presentation
from pptx.util import Inches
import subprocess
import shutil
from dotenv import load_dotenv
import bcrypt
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from config import Config
from models import User, Proposal, Element
import io
import re

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

# Use the same MongoDB URI as the rest of the app (users, templates, etc.)
MONGO_URI = os.getenv("MONGO_URI", Config.MONGO_URI)
LIBRARY_DIR = os.getenv("LIBRARY_DIR", str(Path(__file__).resolve().parents[1] / "Propale_library"))
CACHE_DIR = os.getenv("CACHE_DIR", str(Path(__file__).resolve().parents[1] / "Propale_cache"))
LIBREOFFICE_PATH = os.getenv("LIBREOFFICE_PATH", "")

client = MongoClient(MONGO_URI)
db = client.get_default_database()
templates_col = db["templates"]

cache_path = Path(CACHE_DIR)
cache_path.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────
CORS(app)
jwt = JWTManager(app)

# Ensure uploads directory exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def validate_password_strength(password):
    if len(password) < 8:
        return "Password must contain at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return "Password must contain at least one special character"
    return None


def normalize_email(email):
    if email is None:
        return None
    return str(email).strip().lower()


def _parse_bool(value, default=False):
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in ("1", "true", "yes", "y", "on")


def _range_window(range_key: str, now: datetime):
    """
    Returns (start, end, bucket) where bucket is 'day'|'week'|'month'.
    For 'all', start is None.
    """
    key = (range_key or "").strip().lower()
    if key in ("7", "7d", "7j"):
        return (datetime.utcfromtimestamp(now.timestamp() - 7 * 86400), now, "day")
    if key in ("30", "30d", "30j"):
        return (datetime.utcfromtimestamp(now.timestamp() - 30 * 86400), now, "day")
    if key in ("3m", "90d", "90j"):
        return (datetime.utcfromtimestamp(now.timestamp() - 90 * 86400), now, "week")
    if key in ("12m", "365d", "365j", "1y"):
        return (datetime.utcfromtimestamp(now.timestamp() - 365 * 86400), now, "month")
    if key in ("all", "tout"):
        return (None, now, "month")
    return (datetime.utcfromtimestamp(now.timestamp() - 30 * 86400), now, "day")


def _shift_window(start: datetime | None, end: datetime):
    if start is None:
        return (None, None)
    seconds = int(end.timestamp() - start.timestamp())
    prev_end = start
    prev_start = datetime.utcfromtimestamp(prev_end.timestamp() - seconds)
    return (prev_start, prev_end)


def _bucket_key(dt: datetime, bucket: str):
    if bucket == "month":
        return dt.strftime("%Y-%m")
    if bucket == "week":
        iso = dt.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return dt.strftime("%Y-%m-%d")


def _safe_int(value, default=0):
    try:
        if value is None:
            return default
        return int(value)
    except Exception:
        return default


def _is_admin_user(user_doc: dict | None):
    if not user_doc:
        return False
    if user_doc.get("is_admin") is True:
        return True
    admin_emails = [e.strip().lower() for e in str(os.getenv("ADMIN_EMAILS", "")).split(",") if e.strip()]
    if not admin_emails:
        return False
    email = normalize_email(user_doc.get("email"))
    return bool(email and email in admin_emails)

@app.route("/api/health")
def health():
    soffice = find_soffice()
    return jsonify({
        "status": "ok",
        "message": "Backend is running",
        "libreoffice": soffice or "not found",
        "pdftoppm": shutil.which("pdftoppm") or "not found",
    })


@app.route("/")
def root():
    return jsonify({"message": "Welcome to the Flask API"})


# ─────────────────────────────────────────────
# LibreOffice detection (robust cross-platform)
# ─────────────────────────────────────────────

def find_soffice() -> str | None:
    """
    Locate the LibreOffice `soffice` executable.
    Checks (in order):
      1. LIBREOFFICE_PATH env var
      2. PATH (shutil.which)
      3. Common Windows install locations
      4. Common Linux/macOS install locations
    Returns the path string if found, else None.
    """
    # 1. Explicit env var
    if LIBREOFFICE_PATH and Path(LIBREOFFICE_PATH).exists():
        return LIBREOFFICE_PATH

    # 2. PATH
    found = shutil.which("soffice")
    if found:
        return found

    # 3. Windows candidates
    windows_candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        r"C:\Program Files\LibreOffice 7\program\soffice.exe",
        r"C:\Program Files\LibreOffice 6\program\soffice.exe",
        # Dynamic: scan Program Files for any LibreOffice version
        *glob.glob(r"C:\Program Files\LibreOffice*\program\soffice.exe"),
        *glob.glob(r"C:\Program Files (x86)\LibreOffice*\program\soffice.exe"),
    ]
    for c in windows_candidates:
        if c and Path(c).exists():
            return c

    # 4. Linux / macOS candidates
    unix_candidates = [
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
        "/opt/libreoffice/program/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        *glob.glob("/opt/libreoffice*/program/soffice"),
    ]
    for c in unix_candidates:
        if c and Path(c).exists():
            return c

    return None


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_slide_count(file_path: Path) -> int:
    try:
        prs = Presentation(str(file_path))
        return len(prs.slides)
    except Exception:
        return 0


def ensure_pdf(file_path: Path) -> Path:
    """Convert a PPTX to PDF using LibreOffice. Caches the result."""
    pdf_path = cache_path / f"{file_path.stem}.pdf"
    if pdf_path.exists():
        return pdf_path

    soffice = find_soffice()
    if not soffice:
        raise RuntimeError(
            "LibreOffice (soffice) not found. "
            "Install LibreOffice and set LIBREOFFICE_PATH in your .env, "
            "or add soffice to your PATH."
        )

    subprocess.run(
        [
            soffice,
            "--headless",
            "--convert-to", "pdf",
            "--outdir", str(cache_path),
            str(file_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return pdf_path


def pdf_to_slide_images(pdf_path: Path, stem: str) -> list[str]:
    """
    Convert a PDF to a list of base64-encoded PNG images (one per slide).
    Uses pdftoppm (Poppler). Falls back to PyMuPDF (fitz) if available.
    Returns a list of base64 strings.
    """
    output_prefix = cache_path / f"{stem}_slide"
    images_b64 = []

    # ── Try pdftoppm (Poppler) ──
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        subprocess.run(
            [pdftoppm, "-png", "-r", "120", str(pdf_path), str(output_prefix)],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        image_files = sorted(cache_path.glob(f"{stem}_slide-*.png"))
        for img_file in image_files:
            images_b64.append(base64.b64encode(img_file.read_bytes()).decode())
        return images_b64

    # ── Try PyMuPDF (fitz) ──
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(str(pdf_path))
        for page in doc:
            mat = fitz.Matrix(1.5, 1.5)  # ~108 DPI
            pix = page.get_pixmap(matrix=mat)
            images_b64.append(base64.b64encode(pix.tobytes("png")).decode())
        return images_b64
    except ImportError:
        pass

    raise RuntimeError(
        "No image converter found. "
        "Install Poppler (pdftoppm) or PyMuPDF (`pip install pymupdf`)."
    )


def get_slide_thumbnails_fallback(file_path: Path) -> list[dict]:
    """
    Pure python-pptx fallback: extract slide text & embedded images.
    Used when LibreOffice / Poppler are unavailable.
    Returns a list of dicts with 'index', 'title', 'text', 'image' (base64 or None).
    """
    prs = Presentation(str(file_path))
    slides_data = []
    for i, slide in enumerate(prs.slides):
        title = ""
        texts = []
        first_image_b64 = None

        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    if not title and shape.shape_type == 13 or (hasattr(shape, "placeholder_format") and shape.placeholder_format and shape.placeholder_format.idx == 0):
                        title = t
                    else:
                        texts.append(t)
            # Extract first embedded image
            if first_image_b64 is None and shape.shape_type == 13:  # MSO_SHAPE_TYPE.PICTURE
                try:
                    img_bytes = shape.image.blob
                    first_image_b64 = base64.b64encode(img_bytes).decode()
                except Exception:
                    pass

        slides_data.append({
            "index": i + 1,
            "title": title,
            "text": "\n".join(texts),
            "image": first_image_b64,
            "image_type": "embedded",
        })

    return slides_data


# ─────────────────────────────────────────────
# Library scanning
# ─────────────────────────────────────────────

def scan_library():
    library_path = Path(LIBRARY_DIR)
    if not library_path.exists():
        return 0

    files = list(library_path.glob("*.pptx"))
    ops = []
    now = datetime.utcnow()
    for file in files:
        slide_count = get_slide_count(file)
        ops.append(
            UpdateOne(
                {"filename": file.name},
                {
                    "$set": {
                        "filename": file.name,
                        "path": str(file),
                        "size": file.stat().st_size,
                        "slide_count": slide_count,
                        "updated_at": now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
        )
    if ops:
        templates_col.bulk_write(ops)
    return len(files)


@app.route("/api/templates", methods=["GET"])
def list_templates():
    if request.args.get("scan") == "1":
        scan_library()
    docs = list(templates_col.find({}, {"_id": 0}).sort("filename", 1))
    return jsonify({"items": docs})


@app.route("/api/templates/scan", methods=["POST"])
def scan_templates():
    count = scan_library()
    return jsonify({"count": count})


@app.route("/api/templates/<path:filename>/pdf", methods=["GET"])
def template_pdf(filename: str):
    file_path = Path(LIBRARY_DIR) / filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404
    try:
        pdf_path = ensure_pdf(file_path)
        if not pdf_path.exists():
            return jsonify({"error": "PDF conversion failed"}), 500
        return send_file(pdf_path, mimetype="application/pdf")
    except Exception as exc:
        return jsonify({"error": str(exc)}), 500


@app.route("/api/templates/<path:filename>/slides", methods=["GET"])
def template_slides(filename: str):
    """
    Returns slide previews for a PPTX file.

    Query params:
      - mode: "images" (default) or "text"
          "images" → renders each slide as a PNG via LibreOffice + pdftoppm/PyMuPDF
          "text"   → returns extracted text + embedded images (no LibreOffice needed)

    Response (mode=images):
      {
        "filename": "...",
        "slide_count": N,
        "mode": "images",
        "slides": ["<base64 PNG>", ...]
      }

    Response (mode=text):
      {
        "filename": "...",
        "slide_count": N,
        "mode": "text",
        "slides": [{ "index": 1, "title": "...", "text": "...", "image": "<base64>|null" }, ...]
      }
    """
    file_path = Path(LIBRARY_DIR) / filename
    if not file_path.exists():
        return jsonify({"error": "File not found"}), 404

    mode = request.args.get("mode", "images")

    # ── Text / fallback mode ──
    if mode == "text":
        try:
            slides_data = get_slide_thumbnails_fallback(file_path)
            return jsonify({
                "filename": filename,
                "slide_count": len(slides_data),
                "mode": "text",
                "slides": slides_data,
            })
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    # ── Image mode (default) ──
    try:
        # Check if images already cached
        existing = sorted(cache_path.glob(f"{file_path.stem}_slide-*.png"))
        if existing:
            images_b64 = [base64.b64encode(p.read_bytes()).decode() for p in existing]
        else:
            pdf_path = ensure_pdf(file_path)
            images_b64 = pdf_to_slide_images(pdf_path, file_path.stem)

        return jsonify({
            "filename": filename,
            "slide_count": len(images_b64),
            "mode": "images",
            "slides": images_b64,
        })

    except RuntimeError as exc:
        # LibreOffice or converter not found → suggest fallback
        return jsonify({
            "error": str(exc),
            "fallback_url": f"/api/templates/{filename}/slides?mode=text",
            "hint": "Use ?mode=text for a no-dependency text preview.",
        }), 503

    except Exception as exc:
        return jsonify({"error": str(exc)}), 500
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    email = normalize_email(data['email'])
    password = data['password']
    name = data.get('name')

    password_error = validate_password_strength(password)
    if password_error:
        return jsonify({"error": password_error}), 400

    # Check if user already exists
    if User.find_by_email(email):
        return jsonify({"error": "User already exists"}), 409

    try:
        user_id = User.create_user(email, password, name)
        return jsonify({
            "message": "User created successfully",
            "user_id": user_id
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    email = normalize_email(data['email'])
    password = data['password']

    user = User.find_by_email(email)
    if not user or not User.verify_password(user['password'], password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=str(user['_id']))
    return jsonify({
        "access_token": access_token,
        "user": {
            "id": str(user['_id']),
            "email": user['email'],
            "name": user.get('name'),
            "first_name": user.get('first_name'),
            "last_name": user.get('last_name'),
            "grade": user.get('grade'),
            "department": user.get('department'),
        }
    }), 200


@app.route("/api/auth/change_password", methods=["POST"])
@jwt_required()
def change_password():
    user_id = get_jwt_identity()
    data = request.get_json() or {}

    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "old_password and new_password are required"}), 400

    password_error = validate_password_strength(new_password)
    if password_error:
        return jsonify({"error": password_error}), 400

    try:
        from bson import ObjectId
        user = User.collection.find_one({"_id": ObjectId(user_id)}, {"password": 1})
        if not user:
            return jsonify({"error": "User not found"}), 404

        if not User.verify_password(user["password"], old_password):
            # The user is authenticated (JWT ok) but provided a wrong current password.
            # Return a validation error (not an auth/session error).
            return jsonify({"error": "Old password is incorrect"}), 400

        hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
        User.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"password": hashed_password, "updated_at": datetime.utcnow()}},
        )

        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats/usage", methods=["GET"])
@jwt_required()
def stats_usage():
    """
    Usage statistics for the PowerPoint automation tool.
    Default scope is per-user ("me"). Admins can request scope=all.

    Query params:
      - range: 7d | 30d | 3m | 12m | all
      - compare: 0/1 (compare with previous period)
      - scope: me | all
    """
    user_id = get_jwt_identity()
    now = datetime.utcnow()

    range_key = request.args.get("range", "30d")
    compare = _parse_bool(request.args.get("compare"), default=False)
    scope = (request.args.get("scope", "me") or "me").strip().lower()

    start, end, bucket = _range_window(range_key, now)
    if start is None:
        compare = False

    proposals_col = db["proposals"]
    users_col = db["users"]

    # Authorization for global stats
    user_doc = None
    try:
        from bson import ObjectId
        user_doc = users_col.find_one({"_id": ObjectId(user_id)}, {"email": 1, "is_admin": 1})
    except Exception:
        user_doc = users_col.find_one({"_id": user_id}, {"email": 1, "is_admin": 1})

    if scope == "all" and not _is_admin_user(user_doc):
        return jsonify({"error": "Forbidden"}), 403

    prev_start, prev_end = _shift_window(start, end)

    query_start = prev_start if compare and prev_start else start
    q = {}
    if scope != "all":
        q["user_id"] = user_id
    if query_start is not None:
        q["created_at"] = {"$gte": query_start}

    projection = {
        "user_id": 1,
        "created_at": 1,
        "status": 1,
        "error": 1,
        "duration_ms": 1,
        "slides_count": 1,
        "slide_types": 1,
        "template_name": 1,
        "export_format": 1,
    }

    docs = list(proposals_col.find(q, projection).sort("created_at", 1).limit(10000))

    def in_window(d: dict, s: datetime | None, e: datetime):
        dt = d.get("created_at")
        if not isinstance(dt, datetime):
            return False
        if s is not None and dt < s:
            return False
        return dt < e

    current_docs = [d for d in docs if in_window(d, start, end)]
    prev_docs = [d for d in docs if compare and prev_start and prev_end and in_window(d, prev_start, prev_end)]

    def compute(docs_list: list[dict]):
        total = len(docs_list)
        errors = 0
        slides_total = 0
        durations = []
        slide_types = {}
        templates = {}
        exports = {}
        by_bucket = {}
        by_user = {}

        for d in docs_list:
            status_val = d.get("status")
            status = status_val.strip().lower() if isinstance(status_val, str) else "success"
            if status in ("failed", "error"):
                errors += 1

            slides = _safe_int(d.get("slides_count"), default=0)
            if slides <= 0:
                slides = 2
            slides_total += slides

            dur = d.get("duration_ms")
            if isinstance(dur, (int, float)) and dur >= 0:
                durations.append(float(dur))

            st = d.get("slide_types") or {}
            if isinstance(st, dict) and st:
                for k, v in st.items():
                    slide_types[k] = slide_types.get(k, 0) + _safe_int(v, default=0)
            else:
                slide_types["Titre/intro"] = slide_types.get("Titre/intro", 0) + 1
                slide_types["Texte/bullets"] = slide_types.get("Texte/bullets", 0) + 1

            tpl = d.get("template_name")
            tpl_key = str(tpl).strip() if tpl else "Standard"
            templates[tpl_key] = templates.get(tpl_key, 0) + 1

            fmt = d.get("export_format")
            fmt_key = str(fmt).strip().lower() if fmt else "pptx"
            exports[fmt_key] = exports.get(fmt_key, 0) + 1

            dt = d.get("created_at")
            if isinstance(dt, datetime):
                b = _bucket_key(dt, bucket)
                if b not in by_bucket:
                    by_bucket[b] = {"presentations": 0, "slides": 0, "errors": 0}
                by_bucket[b]["presentations"] += 1
                by_bucket[b]["slides"] += slides
                if status in ("failed", "error"):
                    by_bucket[b]["errors"] += 1

            uid = d.get("user_id")
            if scope == "all" and uid:
                uid_key = str(uid)
                if uid_key not in by_user:
                    by_user[uid_key] = {"presentations": 0, "slides": 0, "errors": 0, "durations": []}
                by_user[uid_key]["presentations"] += 1
                by_user[uid_key]["slides"] += slides
                if status in ("failed", "error"):
                    by_user[uid_key]["errors"] += 1
                if isinstance(dur, (int, float)) and dur >= 0:
                    by_user[uid_key]["durations"].append(float(dur))

        success = total - errors
        success_rate = (success / total) * 100 if total else 0.0
        avg_dur = sum(durations) / len(durations) if durations else None
        min_dur = min(durations) if durations else None
        max_dur = max(durations) if durations else None

        slide_types_rows = [{"label": k, "value": v} for k, v in slide_types.items()]
        slide_types_rows.sort(key=lambda x: x["value"], reverse=True)

        template_rows = [{"label": k, "value": v} for k, v in templates.items()]
        template_rows.sort(key=lambda x: x["value"], reverse=True)

        export_rows = [{"label": k.upper(), "value": v} for k, v in exports.items()]
        export_rows.sort(key=lambda x: x["value"], reverse=True)

        buckets = [{"key": k, **v} for k, v in by_bucket.items()]
        buckets.sort(key=lambda x: x["key"])

        users_rows = []
        if scope == "all" and by_user:
            ids = list(by_user.keys())
            user_map = {}
            try:
                from bson import ObjectId
                obj_ids = []
                for s in ids:
                    try:
                        obj_ids.append(ObjectId(s))
                    except Exception:
                        pass
                if obj_ids:
                    for u in users_col.find({"_id": {"$in": obj_ids}}, {"first_name": 1, "last_name": 1, "email": 1, "department": 1}):
                        user_map[str(u["_id"])] = u
            except Exception:
                pass

            for uid, agg in by_user.items():
                u = user_map.get(uid) or {}
                fn = (u.get("first_name") or "").strip()
                ln = (u.get("last_name") or "").strip()
                label = (f"{fn} {ln}".strip()) or (u.get("email") or uid)
                durs = agg.get("durations") or []
                avg_u = sum(durs) / len(durs) if durs else None
                users_rows.append({
                    "user_id": uid,
                    "label": label,
                    "department": u.get("department"),
                    "presentations": agg["presentations"],
                    "slides": agg["slides"],
                    "errors": agg["errors"],
                    "avg_duration_ms": avg_u,
                })
            users_rows.sort(key=lambda x: x["presentations"], reverse=True)

        return {
            "presentations_total": total,
            "slides_total": slides_total,
            "avg_duration_ms": avg_dur,
            "min_duration_ms": min_dur,
            "max_duration_ms": max_dur,
            "errors_total": errors,
            "success_rate": success_rate,
            "avg_slides_per_presentation": (slides_total / total) if total else 0.0,
            "activity": buckets,
            "slide_types": slide_types_rows,
            "templates": template_rows,
            "exports": export_rows,
            "users": users_rows[:10],
        }

    current = compute(current_docs)
    previous = compute(prev_docs) if compare else None

    return jsonify({
        "range": {
            "key": range_key,
            "start": start.isoformat() if start else None,
            "end": end.isoformat(),
            "bucket": bucket,
            "compare": compare,
            "scope": scope,
        },
        "current": current,
        "previous": previous,
    }), 200


@app.route("/api/proposals", methods=["GET"])
@jwt_required()
def get_proposals():
    user_id = get_jwt_identity()
    proposals = Proposal.find_by_user(user_id)

    # Convert ObjectId to string for JSON serialization
    for proposal in proposals:
        proposal['_id'] = str(proposal['_id'])
        proposal['user_id'] = str(proposal['user_id'])

    return jsonify({"proposals": proposals}), 200


@app.route("/api/generate_proposal", methods=["POST"])
@jwt_required()
def generate_proposal():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('title') or not data.get('content'):
        return jsonify({"error": "Title and content are required"}), 400

    title = data['title']
    content = data['content']

    started = time.time()

    # Save proposal to database early to get an id
    proposal_id = Proposal.create_proposal(user_id, title, content)

    try:
        # Create PowerPoint
        prs = Presentation()

        # Title slide
        title_slide_layout = prs.slide_layouts[0]
        slide = prs.slides.add_slide(title_slide_layout)
        title_placeholder = slide.shapes.title
        title_placeholder.text = title

        # Content slide
        bullet_slide_layout = prs.slide_layouts[1]
        slide = prs.slides.add_slide(bullet_slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = "Details de la Proposition"
        body_shape = shapes.placeholders[1]
        tf = body_shape.text_frame
        tf.text = content

        slides_count = len(prs.slides)

        # Save to file
        filename = f"proposal_{proposal_id}.pptx"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        prs.save(filepath)

        pptx_url = f"/api/download/{filename}"
        Proposal.update_pptx_url(proposal_id, pptx_url)

        duration_ms = int((time.time() - started) * 1000)

        # Enrich proposal with analytics-friendly fields (best-effort)
        try:
            from bson import ObjectId
            db["proposals"].update_one(
                {"_id": ObjectId(proposal_id)},
                {"$set": {
                    "status": "success",
                    "duration_ms": duration_ms,
                    "slides_count": slides_count,
                    "export_format": "pptx",
                    "template_name": "Standard",
                    "slide_types": {
                        "Titre/intro": 1,
                        "Texte/bullets": 1,
                    },
                    "updated_at": datetime.utcnow(),
                }},
            )
        except Exception:
            pass

        return jsonify({
            "message": "Proposal generated successfully",
            "proposal_id": proposal_id,
            "download_url": pptx_url
        }), 201
    except Exception as e:
        # Mark failure for stats (best-effort)
        try:
            from bson import ObjectId
            db["proposals"].update_one(
                {"_id": ObjectId(proposal_id)},
                {"$set": {
                    "status": "failed",
                    "error": str(e),
                    "updated_at": datetime.utcnow(),
                }},
            )
        except Exception:
            pass
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<filename>")
def download_file(filename):
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename)
    return jsonify({"error": "File not found"}), 404


@app.route("/api/elements", methods=["POST"])
@jwt_required()
def create_element():
    user_id = get_jwt_identity()
    data = request.get_json()

    if not data or not data.get('name'):
        return jsonify({"error": "name is required"}), 400

    element_id = Element.create_element(
        user_id=user_id,
        name=data['name'],
        value=data.get('value'),
        metadata=data.get('metadata')
    )

    return jsonify({
        "message": "Element created successfully",
        "element_id": element_id
    }), 201


@app.route("/api/elements", methods=["GET"])
@jwt_required()
def get_elements():
    user_id = get_jwt_identity()
    elements = Element.find_by_user(user_id)

    for element in elements:
        element['_id'] = str(element['_id'])
        element['user_id'] = str(element['user_id'])

    return jsonify({"elements": elements}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
