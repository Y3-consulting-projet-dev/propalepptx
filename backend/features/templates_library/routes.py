from pathlib import Path

from flask import Blueprint, jsonify, request, send_file

from extensions import LIBRARY_DIR, templates_col
from shared.pptx_utils import ensure_pdf, get_slide_count, slides_fallback_text, slides_to_images
from shared.time_utils import utc_now

from .service import scan_library

templates_bp = Blueprint("templates", __name__, url_prefix="/api/templates")


@templates_bp.route("/upload", methods=["POST"])
def upload_template():
    """
    Upload one or more .pptx files to the library.
    multipart/form-data, field name: "files"
    Returns: { "uploaded": [{ filename, slide_count }], "errors": [...] }
    """
    if "files" not in request.files:
        return jsonify({"error": "No files field in request"}), 400

    lib = Path(LIBRARY_DIR)
    lib.mkdir(parents=True, exist_ok=True)

    uploaded, errors = [], []
    now = utc_now()

    for f in request.files.getlist("files"):
        if not f.filename:
            continue
        if not f.filename.lower().endswith(".pptx"):
            errors.append({"filename": f.filename, "error": "Seuls les fichiers .pptx sont acceptés"})
            continue

        safe_name = Path(f.filename).name
        dest = lib / safe_name

        if dest.exists():
            stem = safe_name[:-5]
            suffix = utc_now().strftime("%Y%m%d%H%M%S")
            safe_name = f"{stem}_{suffix}.pptx"
            dest = lib / safe_name

        try:
            f.save(str(dest))
            slide_count = get_slide_count(dest)
            templates_col.update_one(
                {"filename": safe_name},
                {
                    "$set": {
                        "filename":    safe_name,
                        "path":        str(dest),
                        "size":        dest.stat().st_size,
                        "slide_count": slide_count,
                        "updated_at":  now,
                    },
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
            )
            uploaded.append({"filename": safe_name, "slide_count": slide_count})
        except Exception as e:
            errors.append({"filename": safe_name, "error": str(e)})

    return jsonify({"uploaded": uploaded, "errors": errors}), 201


@templates_bp.route("", methods=["GET"])
def list_templates():
    if request.args.get("scan") == "1":
        scan_library()
    return jsonify({"items": list(templates_col.find({}, {"_id": 0}).sort("filename", 1))})


@templates_bp.route("/scan", methods=["POST"])
def scan_templates():
    return jsonify({"count": scan_library()})


@templates_bp.route("/<path:filename>/pdf", methods=["GET"])
def template_pdf(filename: str):
    fp = Path(LIBRARY_DIR) / filename
    if not fp.exists():
        return jsonify({"error": "File not found"}), 404
    try:
        return send_file(ensure_pdf(fp), mimetype="application/pdf")
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@templates_bp.route("/<path:filename>/slides", methods=["GET"])
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
