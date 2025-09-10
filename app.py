from flask import Flask, render_template, request, redirect, url_for, abort
import sqlite3
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "static/images/"

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

# function used to efficiently run queries
def query(query, param=(), commit=False):
    with sqlite3.connect("database.db") as conn:
        cur = conn.cursor()
        cur.execute(query, param)
        if commit:  # determine wheather to insert of return a set of values
            conn.commit()
            return cur.lastrowid 
        else:
            return cur.fetchall()

# function to determine if uploaded files are allowed
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


@app.route('/')  # home page
def home():
    tags = query("SELECT name, icon FROM Tag")
    assets_data = query("SELECT id, name FROM asset")

    # creates a list of assets so it can be processed with its tags
    processed_assets = []
    for asset_row in assets_data:
        asset_info = []
        for item in asset_row:
            asset_info.append(item)
        processed_assets.append(asset_info)

    # asigns the assets tags to each asset
    for asset in processed_assets:
        associated_tags = query(
            "SELECT name, icon FROM Tag WHERE ID IN \
            (SELECT Tag_ID FROM assetTags WHERE Model_ID = ?)",
            (asset[0],)
        )
        asset.append(associated_tags)

    return render_template('home.html',
                           tags=tags,
                           assets=processed_assets,
                           show_navbar=True)


# error function that can be used to display a wide variety of errors
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=e), 404


# upload page where the user uploads new assets
@app.route('/upload', methods=["GET", "POST"])
def upload():
    # runs if just opening the page and not pressing the upload button
    if request.method == "GET":
        tags = query("SELECT id, name FROM Tag")
        return render_template('upload.html', show_navbar=False, tags=tags)

    # gets the info from the froms
    name = request.form["name"]
    description = request.form["description"]
    selected_tags = request.form.getlist("tags")

    #  gets all the uploaded files
    files = {
        "d": request.files.get("diffuse"),
        "n": request.files.get("normal"),
        "s": request.files.get("specular"),
        "o": request.files.get("occlusion"),
    }

    # checks if there is at least a diffuse texture
    if not files["d"] or files["d"].filename == "":
        #return render_template("404.html", error="401 No Image Selected")
        abort(404)

    # checks if the files are allowed
    for suffix, file in files.items():
        if file and file.filename != "":
            if not allowed_file(file.filename):
                return render_template("404.html", error="402 Invalid File Type")

    # adds the asset info
    asset_id = query("INSERT INTO asset(name, description) VALUES(?, ?)", (name, description), commit=True)

    # saves the image files and asigns the names so they can be referanced later -
    # using the asset id instead of storing the raw name in the database
    for suffix, file in files.items():
        filename = secure_filename(f"{asset_id}{suffix}.png")
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

    # adds the tags for the asset
    for tag_id in selected_tags:
        query("INSERT INTO assetTags(Model_ID, Tag_ID) VALUES(?, ?)", (asset_id, tag_id), commit=True)

    return redirect(url_for("home"))


# asset page that displays and individual assets information
@app.route('/asset/<int:id>')
def asset(id):
    asset = query("SELECT id,name,description FROM asset WHERE ID = ?", (id,))
    assettags = query("SELECT name,icon FROM Tag WHERE ID IN (SELECT Tag_ID FROM assetTags WHERE Model_ID = ?)", (id,))

    if not asset:
        abort(404)

    if not assettags:
        abort(404)

    return render_template('asset.html', show_navbar=False, asset=asset, assettags=assettags)


app.run(debug=True)
