from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
import os
from werkzeug.utils import secure_filename
from PIL import Image

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/images/"

def get_bee_movie():
    try:
        with open('bee.txt', 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        return "Bee movie script not found."

bee_movie = get_bee_movie()
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

def query(query, param=(), commit=False):
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute(query, param)
        if commit:
            conn.commit()
            return cur.lastrowid
        else:
            return cur.fetchall()

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# home page
@app.route('/')
def home():
    tags = query("SELECT name, icon FROM Tag")
    assets_data = query("SELECT id,name,COALESCE(views,0),COALESCE(downloads,0),COALESCE(likes,0),COALESCE(resolution,'Unknown') FROM asset")

    processed_assets = []
    for asset_row in assets_data:
        asset_info = []
        for item in asset_row:
            asset_info.append(item)
        processed_assets.append(asset_info)

    for asset in processed_assets:
        associated_tags = query(
            "SELECT name, icon FROM Tag WHERE ID IN \
            (SELECT Tag_ID FROM assetTags WHERE Model_ID = ?)",
            (asset[0],)
        )
        asset.append(associated_tags)
        
        # Check which image types are available for this asset
        available_types = []
        for suffix in ['d', 'n', 's', 'o']:
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{asset[0]}{suffix}.png")
            if os.path.exists(file_path):
                available_types.append(suffix)
        asset.append(available_types)

    return render_template('home.html', tags=tags, assets=processed_assets, show_navbar=True)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=e), 404

@app.route('/upload', methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        tags = query("SELECT id, name FROM Tag")
        return render_template('upload.html', show_navbar=False, tags=tags)

    name = request.form["name"]
    description = request.form["description"]
    selected_tags = request.form.getlist("tags")

    files = {
        "d": request.files.get("diffuse"),
        "n": request.files.get("normal"),
        "s": request.files.get("specular"),
        "o": request.files.get("occlusion"),
    }

    if not files["d"] or files["d"].filename == "":
        return render_template("404.html", error="401 No Image Selected")

    for suffix, file in files.items():
        if file and file.filename != "":
            if not allowed_file(file.filename):
                return render_template("404.html", error="402 Invalid File Type")

    # --- FIX: Read resolution without consuming the stream permanently ---
    resolution = "Unknown"
    if files["d"] and files["d"].filename != "":
        try:
            with Image.open(files["d"].stream) as img:
                width, height = img.size
                resolution = f"{width}x{height}"
            # rewind so the next save() writes the full file
            files["d"].stream.seek(0)
        except Exception:
            resolution = "Unknown"
    # ----------------------------------------------------------------------

    asset_id = query(
        "INSERT INTO asset(name, description, resolution) VALUES(?, ?, ?)",
        (name, description, resolution), commit=True
    )

    for suffix, file in files.items():
        if file and file.filename != "":
            filename = secure_filename(f"{asset_id}{suffix}.png")
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    for tag_id in selected_tags:
        query("INSERT INTO assetTags(Model_ID, Tag_ID) VALUES(?, ?)", (asset_id, tag_id), commit=True)

    return redirect(url_for("home"))

@app.route('/asset/<int:id>')
def asset(id):
    query("UPDATE asset SET views = COALESCE(views, 0) + 1 WHERE ID = ?", (id,), commit=True)
    asset = query("SELECT id,name,views,downloads,likes,description FROM asset WHERE ID = ?", (id,))
    assettags = query("SELECT name,icon FROM Tag WHERE ID IN (SELECT Tag_ID FROM assetTags WHERE Model_ID = ?)", (id,))

    return render_template('asset.html', show_navbar=False, asset=asset, assettags=assettags)



@app.route('/download/<int:asset_id>/<string:image_type>')
def download_image(asset_id, image_type):
    query("UPDATE asset SET downloads = COALESCE(downloads, 0) + 1 WHERE ID = ?", (asset_id,), commit=True)

    valid_types = ['d', 'n', 's', 'o']
    if image_type not in valid_types:
        return "Invalid image type", 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], f"{asset_id}{image_type}.png")
    if not os.path.exists(file_path):
        return "File not found", 404

    return send_file(file_path, as_attachment=True, download_name=f"{asset_id}{image_type}.png")

app.run(debug=True)
