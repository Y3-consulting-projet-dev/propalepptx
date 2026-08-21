from bson import ObjectId
from flask import Blueprint, jsonify, request

from extensions import clients_col
from shared.serializers import serialize_client
from shared.time_utils import utc_now

clients_bp = Blueprint("clients", __name__, url_prefix="/api/clients")


@clients_bp.route("", methods=["GET"])
def list_clients():
    """
    GET /api/clients?page=1&limit=25&q=search
    Recherche sur company_name, sector, country, responsable_name.
    """
    page  = max(1, int(request.args.get("page", 1)))
    limit = min(100, int(request.args.get("limit", 25)))
    q     = request.args.get("q", "").strip()
    skip  = (page - 1) * limit

    query = {}
    if q:
        query["$or"] = [
            {"company_name":       {"$regex": q, "$options": "i"}},
            {"sector":             {"$regex": q, "$options": "i"}},
            {"country":            {"$regex": q, "$options": "i"}},
            {"responsable_name":   {"$regex": q, "$options": "i"}},
        ]

    total = clients_col.count_documents(query)
    docs  = list(
        clients_col.find(query)
        .sort("company_name", 1)
        .skip(skip)
        .limit(limit)
    )

    return jsonify({
        "items":      [serialize_client(d) for d in docs],
        "total":      total,
        "page":       page,
        "limit":      limit,
        "totalPages": max(1, (total + limit - 1) // limit),
    })


@clients_bp.route("", methods=["POST"])
def create_client():
    data = request.get_json(force=True)

    if not data.get("company_name", "").strip():
        return jsonify({"error": "Le nom du client est requis"}), 400

    now = utc_now()
    doc = {
        "company_name":        data.get("company_name", "").strip(),
        "sector":              data.get("sector", ""),
        "country":             data.get("country", ""),
        "civility":            data.get("civility", ""),
        "responsable_name":    data.get("responsable_name", ""),
        "responsable_function":data.get("responsable_function", ""),
        "legal_form":          data.get("legal_form", ""),
        "RCCM":                data.get("RCCM", ""),
        "address":             data.get("address", ""),
        "creation_date":       data.get("creation_date", ""),
        "created_at":          now,
        "updated_at":          now,
    }
    result = clients_col.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return jsonify(doc), 201


@clients_bp.route("/<client_id>", methods=["GET"])
def get_client(client_id: str):
    try:
        doc = clients_col.find_one({"_id": ObjectId(client_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    if not doc:
        return jsonify({"error": "Client not found"}), 404
    return jsonify(serialize_client(doc))


@clients_bp.route("/<client_id>", methods=["PUT"])
def update_client(client_id: str):
    data = request.get_json(force=True)

    if not data.get("company_name", "").strip():
        return jsonify({"error": "Le nom du client est requis"}), 400

    updates = {
        "company_name":        data.get("company_name", "").strip(),
        "sector":              data.get("sector", ""),
        "country":             data.get("country", ""),
        "civility":            data.get("civility", ""),
        "responsable_name":    data.get("responsable_name", ""),
        "responsable_function":data.get("responsable_function", ""),
        "legal_form":          data.get("legal_form", ""),
        "RCCM":                data.get("RCCM", ""),
        "address":             data.get("address", ""),
        "creation_date":       data.get("creation_date", ""),
        "updated_at":          utc_now(),
    }

    try:
        result = clients_col.update_one({"_id": ObjectId(client_id)}, {"$set": updates})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400

    if result.matched_count == 0:
        return jsonify({"error": "Client not found"}), 404

    doc = clients_col.find_one({"_id": ObjectId(client_id)})
    return jsonify(serialize_client(doc))


@clients_bp.route("/<client_id>", methods=["DELETE"])
def delete_client(client_id: str):
    try:
        result = clients_col.delete_one({"_id": ObjectId(client_id)})
    except Exception:
        return jsonify({"error": "Invalid ID"}), 400
    if result.deleted_count == 0:
        return jsonify({"error": "Client not found"}), 404
    return jsonify({"ok": True})


@clients_bp.route("/meta/sectors", methods=["GET"])
def client_sectors():
    raw = clients_col.distinct("sector")
    sectors = sorted([s for s in raw if s and s.strip()])
    return jsonify({"items": sectors})


@clients_bp.route("/meta/countries", methods=["GET"])
def client_countries():
    raw = clients_col.distinct("country")
    countries = sorted([c for c in raw if c and c.strip()])
    return jsonify({"items": countries})
