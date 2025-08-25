from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config["UPLOAD_FOLDER"] = "static/images/"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}  # ✅ only allow images

def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

@app.route('/')
def home():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT name,icon FROM Tag")
    tags = cur.fetchall()

    cur.execute("SELECT id, name FROM asset")
    assets = cur.fetchall()

    alist = []
    for asset in assets:
        thing = []
        for i in asset:
            thing.append(i)
        alist.append(thing)

    for asset in alist:
        cur.execute("SELECT name,icon FROM Tag WHERE ID IN (SELECT Tag_ID FROM assetTags WHERE Model_ID = ?)", (asset[0],))
        asset.append(cur.fetchall())
    assets = alist

    conn.close()
    return render_template('home.html', tags=tags, assets=assets, show_navbar=True)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=404), 404
@app.route('/upload', methods=["GET", "POST"])
def upload():
    if request.method == "GET":
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM Tag") 
        tags = cursor.fetchall()
        conn.close()
        return render_template('upload.html', show_navbar=False, tags=tags)

    # --- POST handling ---
    name = request.form["name"]
    description = request.form["description"]
    selected_tags = request.form.getlist("tags")

    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    # Files
    files = {
        "d": request.files.get("diffuse"),
        "n": request.files.get("normal"),
        "s": request.files.get("specular"),
        "o": request.files.get("occlusion"),
    }

    # ✅ Require at least diffuse texture
    if not files["d"] or files["d"].filename == "":
        return render_template("404.html", error="401 No Image Selected")

    # ✅ Check file extensions
    for suffix, file in files.items():
        if file and file.filename != "":
            if not allowed_file(file.filename):
                conn.close()
                return render_template("404.html", error="402 Invalid File Type")

    # Insert the asset
    cursor.execute("INSERT INTO asset(name, description) VALUES(?, ?)", (name, description))
    asset_id = cursor.lastrowid

    # Save the allowed images
    for suffix, file in files.items():
        if file and file.filename != "" and allowed_file(file.filename):
            filename = secure_filename(f"{asset_id}{suffix}.png")  # normalize to PNG
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    # Link tags
    for tag_id in selected_tags:
        cursor.execute("INSERT INTO assetTags(Model_ID, Tag_ID) VALUES(?, ?)", (asset_id, tag_id))

    conn.commit()
    conn.close()
    return redirect(url_for("home"))



@app.route('/asset/<int:id>')
def asset(id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id,name,description FROM asset WHERE ID = ?", (id,))
    asset = cur.fetchall()

    creator = "Me"

    cur = conn.cursor()
    cur.execute("SELECT name,icon FROM Tag WHERE ID IN (SELECT Tag_ID FROM assetTags WHERE Model_ID = ?)", (id,))
    assettags = cur.fetchall()
    return render_template('asset.html', show_navbar=False, asset=asset, creator=creator, assettags=assettags)

app.run(debug=True)
