import argparse
import sys
from pathlib import Path

import bcrypt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models import User


def reset_all_passwords(new_password):
    hashed = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())
    result = User.collection.update_many({}, {"$set": {"password": hashed}})
    return result.matched_count, result.modified_count


def main():
    parser = argparse.ArgumentParser(
        description="Reinitialise le mot de passe de tous les utilisateurs a une valeur par defaut."
    )
    parser.add_argument(
        "--password",
        default="Ycube@c2026",
        help="Nouveau mot de passe par defaut (par defaut: Ycube@c2026)",
    )
    args = parser.parse_args()

    matched, modified = reset_all_passwords(args.password)
    print("Reinitialisation terminee.")
    print(f"- Utilisateurs trouves : {matched}")
    print(f"- Mots de passe mis a jour : {modified}")


if __name__ == "__main__":
    main()
