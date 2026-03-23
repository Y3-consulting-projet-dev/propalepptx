from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from pptx import Presentation
from config import Config
from models import User, Proposal
import io
import os

app = Flask(__name__)
app.config.from_object(Config)

CORS(app)
jwt = JWTManager(app)

# Ensure uploads directory exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "message": "Backend is running"})


@app.route("/")
def root():
    return jsonify({"message": "Welcome to the Flask API"})


@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()

    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"error": "Email and password are required"}), 400

    email = data['email']
    password = data['password']
    name = data.get('name')

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

    email = data['email']
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
            "name": user.get('name')
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
