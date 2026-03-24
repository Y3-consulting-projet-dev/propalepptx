import argparse
from datetime import datetime
from openpyxl import load_workbook
import bcrypt

from models import User


def normalize_email(value):
    if value is None:
        return None
    email = str(value).strip().lower()
    return email or None


def build_full_name(last_name, first_name):
    parts = []
    if first_name:
        parts.append(str(first_name).strip())
    if last_name:
        parts.append(str(last_name).strip())
    return " ".join([p for p in parts if p]) or None


def import_users_from_excel(file_path, default_password, reset_password=False):
    wb = load_workbook(file_path, read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]

    rows = ws.iter_rows(min_row=1, values_only=True)
    headers = next(rows)
    header_map = {str(h).strip().lower(): idx for idx, h in enumerate(headers) if h}

    required_headers = ["nom", "prenoms", "mail"]
    missing = [h for h in required_headers if h not in header_map]
    if missing:
        raise ValueError(f"Colonnes manquantes dans le fichier Excel: {', '.join(missing)}")

    nom_idx = header_map["nom"]
    prenoms_idx = header_map["prenoms"]
    mail_idx = header_map["mail"]
    grade_idx = header_map.get("grade")
    dep_idx = header_map.get("departement")

    hashed_password = bcrypt.hashpw(default_password.encode("utf-8"), bcrypt.gensalt())
    now = datetime.utcnow()

    inserted = 0
    updated = 0
    skipped = 0

    for row in rows:
        email = normalize_email(row[mail_idx] if mail_idx < len(row) else None)
        if not email:
            skipped += 1
            continue

        last_name = row[nom_idx] if nom_idx < len(row) else None
        first_name = row[prenoms_idx] if prenoms_idx < len(row) else None
        name = build_full_name(last_name, first_name)

        profile_updates = {
            "name": name,
            "last_name": str(last_name).strip() if last_name else None,
            "first_name": str(first_name).strip() if first_name else None,
            "grade": str(row[grade_idx]).strip() if grade_idx is not None and row[grade_idx] else None,
            "department": str(row[dep_idx]).strip() if dep_idx is not None and row[dep_idx] else None,
            "is_active": True,
            "updated_at": now,
        }

        existing_user = User.find_by_email(email)
        if existing_user:
            update_doc = {"$set": profile_updates}
            if reset_password:
                update_doc["$set"]["password"] = hashed_password
            User.collection.update_one({"_id": existing_user["_id"]}, update_doc)
            updated += 1
        else:
            user_data = {
                "email": email,
                "password": hashed_password,
                "created_at": now,
                **profile_updates,
            }
            User.collection.insert_one(user_data)
            inserted += 1

    return inserted, updated, skipped


def main():
    parser = argparse.ArgumentParser(
        description="Importer le registre du personnel dans la collection users de MongoDB."
    )
    parser.add_argument("--file", required=True, help="Chemin du fichier Excel (.xlsx)")
    parser.add_argument(
        "--default-password",
        required=True,
        help="Mot de passe par defaut assigne aux nouveaux utilisateurs",
    )
    parser.add_argument(
        "--reset-password",
        action="store_true",
        help="Reinitialise aussi le mot de passe des utilisateurs deja existants",
    )
    args = parser.parse_args()

    inserted, updated, skipped = import_users_from_excel(
        file_path=args.file,
        default_password=args.default_password,
        reset_password=args.reset_password,
    )

    print("Import termine.")
    print(f"- Nouveaux utilisateurs : {inserted}")
    print(f"- Utilisateurs mis a jour : {updated}")
    print(f"- Lignes ignorees (email vide) : {skipped}")


if __name__ == "__main__":
    main()
