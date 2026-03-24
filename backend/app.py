import io
import os
import re
import uuid
import base64
import glob
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from pptx.util import Inches
import anthropic
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from pymongo import MongoClient, UpdateOne
from pptx import Presentation
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from config import Config
from models import User, Proposal, Element

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)
jwt = JWTManager(app)

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────

MONGO_URI = os.getenv("MONGO_URI", Config.MONGO_URI)
LIBRARY_DIR = os.getenv("LIBRARY_DIR", str(Path(__file__).resolve().parents[1] / "Propale_library"))
CACHE_DIR = os.getenv("CACHE_DIR", str(Path(__file__).resolve().parents[1] / "Propale_cache"))
OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(Path(__file__).resolve().parents[1] / "Propale_output"))
LIBREOFFICE_PATH  = os.getenv("LIBREOFFICE_PATH",  "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

mongo_client      = MongoClient(MONGO_URI)
db                = mongo_client.get_default_database()
templates_col     = db["templates"]
presentations_col = db["presentations"]

cache_path  = Path(CACHE_DIR)
output_path = Path(OUTPUT_DIR)
cache_path.mkdir(parents=True, exist_ok=True)
output_path.mkdir(parents=True, exist_ok=True)

ai = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


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

# ─────────────────────────────────────────────
# LibreOffice detection
# ─────────────────────────────────────────────

def find_soffice() -> str | None:
    if LIBREOFFICE_PATH and Path(LIBREOFFICE_PATH).exists():
        return LIBREOFFICE_PATH
    found = shutil.which("soffice")
    if found:
        return found
    for c in [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        *glob.glob(r"C:\Program Files\LibreOffice*\program\soffice.exe"),
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
        "/Applications/LibreOffice.app/Contents/MacOS/soffice",
        *glob.glob("/opt/libreoffice*/program/soffice"),
    ]:
        if c and Path(c).exists():
            return c
    return None


# ─────────────────────────────────────────────
# PPTX helpers
# ─────────────────────────────────────────────

def get_slide_count(file_path: Path) -> int:
    try:
        return len(Presentation(str(file_path)).slides)
    except Exception:
        return 0


def extract_slides_text(file_path: Path) -> list[dict]:
    """
    Extract every text shape from a PPTX.
    Returns a list usable both as Claude input and as injection blueprint.
    """
    prs = Presentation(str(file_path))
    result = []
    for slide_idx, slide in enumerate(prs.slides):
        shapes_data = []
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            texts = [p.text for p in shape.text_frame.paragraphs]
            if not any(t.strip() for t in texts):
                continue
            ph_idx = None
            try:
                if shape.is_placeholder:
                    ph_idx = shape.placeholder_format.idx
            except Exception:
                ph_idx = None
            shapes_data.append({
                "shape_id":        shape.shape_id,
                "shape_name":      shape.name,
                "placeholder_idx": ph_idx,
                "texts":           texts,
            })
        result.append({"slide_index": slide_idx, "shapes": shapes_data})
    return result


def inject_content_into_pptx(template_path: Path, content: list[dict], out_file: Path):
    """
    Copy template and replace paragraph texts while preserving all formatting.
    `content` has the same shape as extract_slides_text() output.
    """
    prs = Presentation(str(template_path))

    # Build lookup (slide_index, shape_id) → list of new paragraph strings
    lookup: dict[tuple, list[str]] = {}
    for slide_data in content:
        for shape_data in slide_data["shapes"]:
            lookup[(slide_data["slide_index"], shape_data["shape_id"])] = shape_data["texts"]

    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            new_texts = lookup.get((slide_idx, shape.shape_id))
            if new_texts is None or not shape.has_text_frame:
                continue
            for para_idx, para in enumerate(shape.text_frame.paragraphs):
                new_text = new_texts[para_idx] if para_idx < len(new_texts) else ""
                if para.runs:
                    para.runs[0].text = new_text
                    for run in para.runs[1:]:
                        run.text = ""

    prs.save(str(out_file))


def ensure_pdf(file_path: Path, stem: str | None = None) -> Path:
    stem = stem or file_path.stem
    pdf_path = cache_path / f"{stem}.pdf"
    if pdf_path.exists():
        return pdf_path
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice not found. Install it or set LIBREOFFICE_PATH.")
    # soffice names the output after the input file stem — use a symlink trick
    tmp = cache_path / f"{stem}.pptx"
    if str(tmp) != str(file_path):
        shutil.copy2(str(file_path), str(tmp))
    subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", str(cache_path), str(tmp)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return pdf_path


def pdf_to_images(pdf_path: Path, stem: str) -> list[str]:
    prefix = cache_path / f"{stem}_slide"
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm:
        subprocess.run(
            [pdftoppm, "-png", "-r", "120", str(pdf_path), str(prefix)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        return [base64.b64encode(p.read_bytes()).decode()
                for p in sorted(cache_path.glob(f"{stem}_slide-*.png"))]
    try:
        import fitz
        doc = fitz.open(str(pdf_path))
        return [base64.b64encode(page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).tobytes("png")).decode()
                for page in doc]
    except ImportError:
        pass
    raise RuntimeError("Install poppler-utils (pdftoppm) or pymupdf.")


def slides_to_images(pptx_path: Path, stem: str) -> list[str]:
    existing = sorted(cache_path.glob(f"{stem}_slide-*.png"))
    if existing:
        return [base64.b64encode(p.read_bytes()).decode() for p in existing]
    return pdf_to_images(ensure_pdf(pptx_path, stem=stem), stem)


def slides_fallback_text(file_path: Path) -> list[dict]:
    prs = Presentation(str(file_path))
    out = []
    for i, slide in enumerate(prs.slides):
        title, texts, img = "", [], None
        for shape in slide.shapes:
            if shape.has_text_frame:
                t = shape.text_frame.text.strip()
                if t:
                    ph = getattr(shape, "placeholder_format", None)
                    if not title and ph and ph.idx == 0:
                        title = t
                    else:
                        texts.append(t)
            if img is None and shape.shape_type == 13:
                try:
                    img = base64.b64encode(shape.image.blob).decode()
                except Exception:
                    pass
        out.append({"index": i + 1, "title": title, "text": "\n".join(texts), "image": img})
    return out


def invalidate_image_cache(stem: str):
    for f in cache_path.glob(f"{stem}_slide-*.png"):
        f.unlink(missing_ok=True)
    (cache_path / f"{stem}.pdf").unlink(missing_ok=True)


# ─────────────────────────────────────────────
# Claude AI — content generation
# ─────────────────────────────────────────────

SYSTEM_PROMPT = """Tu es un expert en rédaction de propositions commerciales et présentations professionnelles pour des cabinets d'audit et de conseil en Afrique francophone.

Tu reçois :
1. La structure d'un fichier PPTX (slides + shapes avec leurs textes actuels)
2. Les informations du formulaire remplies par l'utilisateur

Règles STRICTES :
- Remplace les textes génériques/placeholders par du vrai contenu professionnel personnalisé
- Garde EXACTEMENT le même nombre d'éléments dans chaque tableau "texts" (même nombre de paragraphes)
- Utilise les informations du formulaire pour tout personnaliser (client, secteur, mission, etc.)
- Rédige en français professionnel, concis
- Titres courts (1 ligne max), bullets concis (1-2 phrases)
- Ne modifie PAS les numéros de page, logos texte, ni les textes purement décoratifs
- Réponds UNIQUEMENT avec le JSON, aucun texte avant ou après, pas de backticks markdown"""


def generate_content_with_claude(slides_structure: list[dict], form_data: dict) -> list[dict]:
    user_message = (
        f"Informations de la mission :\n{json.dumps(form_data, ensure_ascii=False, indent=2)}\n\n"
        f"Structure du modèle PPTX :\n{json.dumps(slides_structure, ensure_ascii=False, indent=2)}\n\n"
        "Génère le contenu professionnel en JSON."
    )
    msg = ai.messages.create(
        model="claude-opus-4-5",
        max_tokens=8192,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    raw = msg.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ─────────────────────────────────────────────
# MongoDB serialization
# ─────────────────────────────────────────────

def serialize(doc: dict) -> dict:
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


# ─────────────────────────────────────────────
# Library scanning
# ─────────────────────────────────────────────

def scan_library() -> int:
    lib = Path(LIBRARY_DIR)
    if not lib.exists():
        return 0
    ops, now = [], datetime.utcnow()
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


# ─────────────────────────────────────────────
# Routes — health
# ─────────────────────────────────────────────

@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "libreoffice": find_soffice() or "not found",
        "pdftoppm":    shutil.which("pdftoppm") or "not found",
        "anthropic":   "key set" if ANTHROPIC_API_KEY else "KEY MISSING — set ANTHROPIC_API_KEY in .env",
    })


@app.route("/")
def root():
    return jsonify({"message": "Propale API v1"})


# ─────────────────────────────────────────────
# Routes — Templates
# ─────────────────────────────────────────────

@app.route("/api/templates", methods=["GET"])
def list_templates():
    if request.args.get("scan") == "1":
        scan_library()
    return jsonify({"items": list(templates_col.find({}, {"_id": 0}).sort("filename", 1))})


@app.route("/api/templates/scan", methods=["POST"])
def scan_templates():
    return jsonify({"count": scan_library()})


@app.route("/api/templates/<path:filename>/pdf", methods=["GET"])
def template_pdf(filename: str):
    fp = Path(LIBRARY_DIR) / filename
    if not fp.exists():
        return jsonify({"error": "File not found"}), 404
    try:
        return send_file(ensure_pdf(fp), mimetype="application/pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/templates/<path:filename>/slides", methods=["GET"])
def template_slides(filename: str):
    fp = Path(LIBRARY_DIR) / filename
    if not fp.exists():
        return jsonify({"error": "File not found"}), 404
    mode = request.args.get("mode", "images")
    if mode == "text":
        try:
            s = slides_fallback_text(fp)
            return jsonify({"slide_count": len(s), "mode": "text", "slides": s})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    try:
        imgs = slides_to_images(fp, fp.stem)
        return jsonify({"filename": filename, "slide_count": len(imgs), "mode": "images", "slides": imgs})
    except RuntimeError as e:
        return jsonify({"error": str(e), "fallback_url": f"/api/templates/{filename}/slides?mode=text"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────
# Routes — Generate
# ─────────────────────────────────────────────

@app.route("/api/generate", methods=["POST"])
def generate_presentation():
    """
    POST /api/generate
    Body: { "template_filename": "...", "form": { clientName, sector, … } }
    Returns: { "presentation_id": "…", "slide_count": N }
    """
    body = request.get_json(force=True)
    tmpl_file = body.get("template_filename")
    form_data = body.get("form", {})

    if not tmpl_file:
        return jsonify({"error": "template_filename is required"}), 400
    if not ANTHROPIC_API_KEY:
        return jsonify({"error": "ANTHROPIC_API_KEY not set in .env"}), 500

    tmpl_path = Path(LIBRARY_DIR) / tmpl_file
    if not tmpl_path.exists():
        return jsonify({"error": f"Template not found: {tmpl_file}"}), 404

    # Step 1 — extract template structure
    try:
        structure = extract_slides_text(tmpl_path)
    except Exception as e:
        return jsonify({"error": f"Cannot read template: {e}"}), 500

    # Step 2 — generate content with Claude
    try:
        generated = generate_content_with_claude(structure, form_data)
    except json.JSONDecodeError as e:
        return jsonify({"error": f"Claude returned malformed JSON: {e}"}), 500
    except Exception as e:
        return jsonify({"error": f"AI generation error: {e}"}), 500

    # Step 3 — build PPTX
    pres_id  = str(uuid.uuid4())
    out_name = f"propale_{pres_id}.pptx"
    out_file = output_path / out_name
    try:
        inject_content_into_pptx(tmpl_path, generated, out_file)
    except Exception as e:
        return jsonify({"error": f"PPTX creation failed: {e}"}), 500

    slide_count = get_slide_count(out_file)

    # Step 4 — persist
    now = datetime.utcnow()
    doc = {
        "presentation_id": pres_id,
        "filename":        out_name,
        "path":            str(out_file),
        "template":        tmpl_file,
        "form":            form_data,
        "slide_count":     slide_count,
        "status":          "draft",
        "created_at":      now,
        "updated_at":      now,
    }
    result = presentations_col.insert_one(doc)

    # Step 5 — pre-render slide images (best-effort, non-blocking)
    try:
        slides_to_images(out_file, pres_id)
    except Exception:
        pass

    return jsonify({
        "presentation_id": pres_id,
        "mongo_id":        str(result.inserted_id),
        "filename":        out_name,
        "slide_count":     slide_count,
    }), 201


# ─────────────────────────────────────────────
# Routes — Presentations
# ─────────────────────────────────────────────

@app.route("/api/presentations", methods=["GET"])
def list_presentations():
    docs = list(presentations_col.find().sort("created_at", -1))
    return jsonify({"items": [serialize(d) for d in docs]})


@app.route("/api/presentations/<pres_id>", methods=["GET"])
def get_presentation(pres_id: str):
    doc = presentations_col.find_one({"presentation_id": pres_id})
    if not doc:
        return jsonify({"error": "Not found"}), 404
    return jsonify(serialize(doc))


@app.route("/api/presentations/<pres_id>/slides", methods=["GET"])
def presentation_slides(pres_id: str):
    doc = presentations_col.find_one({"presentation_id": pres_id})
    if not doc:
        return jsonify({"error": "Not found"}), 404
    fp = Path(doc["path"])
    if not fp.exists():
        return jsonify({"error": "PPTX file missing on disk"}), 404
    mode = request.args.get("mode", "images")
    if mode == "text":
        try:
            s = slides_fallback_text(fp)
            return jsonify({"slide_count": len(s), "mode": "text", "slides": s})
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    try:
        imgs = slides_to_images(fp, pres_id)
        return jsonify({"slide_count": len(imgs), "mode": "images", "slides": imgs})
    except RuntimeError as e:
        return jsonify({"error": str(e), "fallback_url": f"/api/presentations/{pres_id}/slides?mode=text"}), 503
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/presentations/<pres_id>/slide/<int:slide_index>", methods=["PATCH"])
def patch_slide(pres_id: str, slide_index: int):
    """
    PATCH /api/presentations/<id>/slide/<n>
    Body: { "shapes": [{ "shape_id": N, "texts": ["para1", "para2"] }] }
    Saves the PPTX and invalidates the image cache for this presentation.
    """
    doc = presentations_col.find_one({"presentation_id": pres_id})
    if not doc:
        return jsonify({"error": "Not found"}), 404
    fp = Path(doc["path"])
    if not fp.exists():
        return jsonify({"error": "PPTX missing"}), 404

    shapes_patch = {s["shape_id"]: s["texts"] for s in request.get_json(force=True).get("shapes", [])}
    try:
        prs   = Presentation(str(fp))
        slide = prs.slides[slide_index]
        for shape in slide.shapes:
            if shape.shape_id not in shapes_patch or not shape.has_text_frame:
                continue
            new_texts = shapes_patch[shape.shape_id]
            for i, para in enumerate(shape.text_frame.paragraphs):
                t = new_texts[i] if i < len(new_texts) else ""
                if para.runs:
                    para.runs[0].text = t
                    for run in para.runs[1:]:
                        run.text = ""
        prs.save(str(fp))
    except Exception as e:
        return jsonify({"error": f"Patch failed: {e}"}), 500

    invalidate_image_cache(pres_id)
    presentations_col.update_one(
        {"presentation_id": pres_id},
        {"$set": {"updated_at": datetime.utcnow()}},
    )
    return jsonify({"ok": True})


@app.route("/api/presentations/<pres_id>/submit", methods=["POST"])
def submit_presentation(pres_id: str):
    doc = presentations_col.find_one({"presentation_id": pres_id})
    if not doc:
        return jsonify({"error": "Not found"}), 404
    presentations_col.update_one(
        {"presentation_id": pres_id},
        {"$set": {"status": "submitted", "submitted_at": datetime.utcnow()}},
    )
    return jsonify({"ok": True, "status": "submitted"})


@app.route("/api/presentations/<pres_id>/download", methods=["GET"])
def download_presentation(pres_id: str):
    doc = presentations_col.find_one({"presentation_id": pres_id})
    if not doc:
        return jsonify({"error": "Not found"}), 404
    fp = Path(doc["path"])
    if not fp.exists():
        return jsonify({"error": "File not found"}), 404
    name = f"Propale_{doc['form'].get('clientName', 'client')}.pptx"
    return send_file(
        fp,
        mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        as_attachment=True,
        download_name=name,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)