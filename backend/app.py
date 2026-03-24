import os
import base64
import glob
from datetime import datetime
from pathlib import Path
from pymongo import MongoClient, UpdateOne
from pptx import Presentation
from pptx.util import Inches
import subprocess
import shutil
from dotenv import load_dotenv
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

    # Save proposal to database
    proposal_id = Proposal.create_proposal(user_id, title, content)

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
    title_shape.text = "Détails de la Proposition"
    body_shape = shapes.placeholders[1]
    tf = body_shape.text_frame
    tf.text = content

    # Save to file
    filename = f"proposal_{proposal_id}.pptx"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    prs.save(filepath)

    # Update proposal with file URL
    pptx_url = f"/api/download/{filename}"
    Proposal.update_pptx_url(proposal_id, pptx_url)

    return jsonify({
        "message": "Proposal generated successfully",
        "proposal_id": proposal_id,
        "download_url": pptx_url
    }), 201


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
