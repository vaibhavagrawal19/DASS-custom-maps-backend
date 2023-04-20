# app.py

# Required imports
import os
from flask import Flask, request, jsonify, send_file
from firebase_admin import credentials, firestore, initialize_app, storage
import functions
from flask_cors import CORS
import os
import io

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Initialize Firestore DB
cred = credentials.Certificate("key.json")
initialize_app(cred, {"storageBucket": "custom-maps-e7b33.appspot.com"})
db = firestore.client()
users_ref = db.collection("users")
maps_ref = db.collection("maps")


@app.route("/delete-map", methods=["DELETE"])
def delete_map():
    """
    route to delete a map
    the DELETE request should contain the following arguments
    {
        map_id: <String>,
        user_id: <String>
    }
    map_id is the ID of the map to be deleted
    user_id is the ID of the user who is sending the DELETE request, the request would be considered only if the user_id = creator of the map.
    """

    try:
        map_id = request.headers.get("map_id")
        user_id = request.headers.get("user_id")

        # print(map_id)
        # print(user_id)

        if not map_id or not user_id:
            return jsonify({"error": "incomplete_form"}), 400

        user_ref = users_ref.document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "user_not_found"}), 404

        user_doc = user_doc.to_dict()

        if not user_doc["is_admin"]:
            return jsonify({"error": "not_admin"}), 403

        map_ref = maps_ref.document(map_id)
        map_doc = map_ref.get()
        if not map_doc.exists:
            return jsonify({"error": "map_not_found"}), 404

        map_doc = map_doc.to_dict()
        # if map_doc["creator_id"] != user_id:
        #     return jsonify({"error": "not_creator"}), 403

        creator_ref = users_ref.document(map_doc["creator_id"])
        if creator_ref:
            creator_doc = creator_ref.get()
            creator_doc = creator_doc.to_dict()
            if map_id in creator_doc["maps"]:
                creator_doc["maps"].remove(map_id)
            creator_ref.update(creator_doc)

        users_snap = users_ref.get()
        all_users = [doc.to_dict() for doc in users_snap]

        for user in all_users:
            if map_id in user["saved_maps"]:
                user_ref_new = users_ref.document(user["id"])
                user["saved_maps"].remove(map_id)

        map_ref.delete()

        return jsonify({"success": True}), 200
    except Exception as e:
        print(e)
        return f"An error occured: {e}", 500


@app.route("/make-admin", methods=["GET"])
def make_admin():
    """
    route to make a user an admin
    the following format is expected for the header of the GET request
    {
        username: <String>,
    }
    username is the name of the user who is to be made an admin
    """
    try:
        username = request.headers.get("username")
        query = users_ref.where("is_admin", "==", username)
        matching_docs = query.get()
        if len(matching_docs) == 0:
            return jsonify({"error": "user_not_found"}), 400

        user_id = str(matching_docs[0].id)
        user_ref = users_ref.document(user_id)
        user_doc = user_ref.get()
        user_doc = user_doc.to_dict()
        user_doc["is_admin"] = True
        user_ref.update(user_doc)

    except Exception as e:
        return f"An error occured: {e}", 500


@app.route("/edit-map", methods=["PATCH"])
def edit_map():
    """
    route to edit a map
    the header of the PATCH request should have the following format:
    {
        map_id: <String>,
        user_id: <String>
    }
    in the body of the PATCH request just send the new map values just like sent for the create-map route
    """
    try:
        map_id = request.headers.get("map_id")
        user_id = request.headers.get("user_id")

        if not map_id or not user_id:
            return jsonify({"error": "incomplete_form"}), 400

        user_ref = users_ref.document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({"error": "user_not_found"}), 404

        user_doc = user_doc.to_dict()

        if not user_doc["is_admin"]:
            return jsonify({"error": "not_admin"}), 403

        map_data = request.json
        map_ref = maps_ref.document(map_id)
        map_doc = map_ref.get()
        if not map_doc.exists:
            return jsonify({"error": "map_not_found"}), 404

        map_ref.update(map_data)
        return jsonify({"success": True}), 200

    except Exception as e:
        return f"An error occured: {e}", 500


@app.route("/save", methods=["GET"])
def save_map():
    try:
        map_id = str(request.headers.get("map_id"))
        user_id = str(request.headers.get("user_id"))

        if not map_id or not user_id:
            return jsonify({"error": "incomplete_form"}), 400

        print(user_id)
        user_ref = users_ref.document(str(user_id))
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({"error": "user_not_found"}), 404

        map_ref = maps_ref.document(str(map_id))
        map_doc = map_ref.get()
        if not map_doc.exists:
            return jsonify({"error": "map_not_found"}), 404

        user_doc = user_doc.to_dict()
        if map_id in user_doc["saved_maps"]:
            return jsonify({"success": True}), 200
        
        user_doc["saved_maps"].append(map_id)
        user_ref.update(user_doc)

        return jsonify({"success": True}), 200

    except Exception as e:
        return f"An error occured: {e}", 500


@app.route("/upload-image", methods=["POST"])
def upload_image():
    try:
        map_id = request.headers.get("map_id")

        if not map_id:
            return jsonify({"error": "incomplete_form"}), 400

        image_file = request.files["image"]
        if not image_file:
            return jsonify({"error": "no_image"}), 400

        image_path = map_id + ".jpg"
        image_file.save(image_path)

        bucket = storage.bucket()
        blob = bucket.blob(image_path)

        blob.upload_from_filename(image_path)

        os.remove(image_path)

        return "Image uploaded successfully!", 200
    except Exception as e:
        return f"An error occured {e}", 500


@app.route("/create-user", methods=["POST"])
def create_user():
    """
    route to create a new user
    the following format is expected for the POST request body
    {
        firstname: <String>,
        lastname: <String>,
        username: <String>,
        password: <String>
    }
    """

    try:
        user = request.json
        args = list(user.keys())
        if "username" not in args or "password" not in args or "firstname" not in args or "lastname" not in args:
            return jsonify({"error": "incomplete_form"}), 400

        user["maps"] = []
        user["saved_maps"] = []
        user["is_admin"] = False
        users_ref.add(user)
        return jsonify({"success": True}), 200

    except Exception as e:
        print(e)
        return f"An error occurred: {e}", 500
    

@app.route("/unsave", methods=["GET"])
def unsave():
    try:
        user_id = request.headers.get("user_id")
        map_id = request.headers.get("map_id")

        if not map_id or not user_id:
            return jsonify({"error": "incomplete_form"}), 400
        
        user_ref = users_ref.document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({"error": "user_not_found"}), 404
        user_doc = user_doc.to_dict()
        if map_id not in user_doc["saved_maps"]:
            return jsonify({"error": "map_not_saved"})
        user_doc["saved_maps"].remove(map_id)
        user_ref.update(user_doc)
        return jsonify({"success": True}), 200
    
    except Exception as e:
        return f"An error occured: {e}", 500
    
@app.route("/get-saved", methods=["GET"])
def get_saved():
    try:
        user_id = request.headers.get("user_id")

        if not user_id:
            return jsonify({"error": "incomplete_form"}), 400
        
        user_ref = users_ref.document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            return jsonify({"error": "user_not_found"}), 404
        
        user_doc = user_doc.to_dict()
        map_details = []

        for map_id in user_doc["saved_maps"]:
            map_ref = maps_ref.document(map_id)
            map_doc = map_ref.get()
            if map_doc.exists:
                map_doc = map_doc.to_dict()
                map_doc["id"] = str(map_ref.id)
                map_details.append(map_doc)
        
        return jsonify({"success": True, "map_data": map_details}), 200

    except Exception as e:
        return f"An error occured: {e}", 500


@app.route("/login", methods=["GET"])
def login():
    """
    route for login to the application
    the GET request should have the following arguments:
    {
        username: <String>,
        password: <String>
    }
    """
    try:
        username = request.headers.get("username")
        password = request.headers.get("password")

        if not username or not password:
            return jsonify({"error": "incomplete_form"}), 400

        # need to fetch all the users
        users_snap = users_ref.get()
        all_users = [doc.to_dict() for doc in users_snap]
        ids = [doc.id for doc in users_snap]

        # adding the id field to the user object
        for user, id in zip(all_users, ids):
            user["id"] = id

        for doc in all_users:
            if doc["username"] == username and doc["password"] == password:
                # return the found user
                return jsonify({"user": doc, "success": True}), 200

        return jsonify({"error": "no_match"}), 403

    except Exception as e:
        return f"An error occured: {e}", 500


@app.route("/list-maps", methods=["GET"])
def list_maps():
    """
    route to list all the maps in the application
    """
    try:
        # need to fetch all the maps
        docs_snap = maps_ref.get()
        all_maps = [doc.to_dict() for doc in docs_snap]
        ids = [doc.id for doc in docs_snap]

        # adding the id field to the map object
        for map, id in zip(all_maps, ids):
            map["id"] = id

        # returning all the map objects
        return jsonify({"all_maps": all_maps, "success": True}), 200
    except Exception as e:
        return f"An error occured: {e}", 500


@app.route("/fetch-image", methods=["GET"])
def fetch_image():
    """
    route to fetch the image of the map which is being explored by the user
    the GET request should contain the following arguments
    {
        map_id: <String>
    }
    map_id is the ID of the map whose image you want to fetch
    """
    map_id = request.headers.get("map_id")

    if not map_id:
        return jsonify({"error": "incomplete_form"}), 400

    map_ref = maps_ref.document(map_id)
    map = map_ref.get()
    if not map.exists:
        return jsonify({"error": "map_not_found"}), 404

    blob = storage.bucket().blob(str(map_id) + ".jpg")
    image_data = blob.download_as_bytes()

    return send_file(io.BytesIO(image_data), mimetype="image/jpg")


@app.route("/fetch-data", methods=["GET"])
def fetch_nodes():
    """
    route to fetch all the data of a particular map
    """
    try:
        map_id = request.headers.get("map_id")
        if not map_id:
            return jsonify({"error": "incomplete_form_data"}), 400

        map_ref = maps_ref.document(map_id)
        map = map_ref.get()
        if not map.exists:
            return jsonify({"error": "map_not_found"}), 403

        map = map.to_dict()
        return jsonify({"map": map}), 200

    except Exception as e:
        return f"An error occured {e}", 500


@app.route("/create-map", methods=["POST"])
def create_map():
    """
    route to create a map (by an admin)
    the POST request should contain a proper map definition along with the user ID of the creator of the map
    """
    try:
        # print(request.json)
        # return 200
        keys = list(request.json.keys())
        # print(keys)
        if (
            "creator_id" not in keys
            or "nodes" not in keys
            or "edges" not in keys
            or "name" not in keys
        ):
            return jsonify({"error": "incomplete_form"}), 401

        # print(request.json["nodes"])

        creator_id = request.json["creator_id"]
        nodes = list(request.json["nodes"])
        edges = list(request.json["edges"])

        # checking if edge data is complete
        for edge in edges:
            keys = list(edge.keys())
            if (
                "node1" not in keys
                or "node2" not in keys
                or "desc12" not in keys
                or "desc21" not in keys
                or "travel-time" not in keys
            ):
                return jsonify({"error": "incomplete_form"}), 400

            if edge["node1"] not in nodes or edge["node2"] not in nodes:
                return jsonify({"error": "invalid_node"}), 403

        # obtaining the user object
        user_ref = users_ref.document(str(creator_id))
        doc = user_ref.get()
        if not doc.exists:
            return jsonify({"error": "user_not_found"}), 403
        doc = doc.to_dict()
        map_data = {
            "name": request.json["name"],
            "creator_id": request.json["creator_id"],
            "edges": request.json["edges"],
            "nodes": request.json["nodes"],
        }
        update_time, new_map_ref = maps_ref.add(map_data)
        doc["maps"].append(str(new_map_ref.id))
        user_ref.update(doc)

        return jsonify({"success": True, "map_id": str(new_map_ref.id)}), 200

    except Exception as e:
        print(e)
        return f"An error occured: {e}", 500


@app.route("/navigate", methods=["GET"])
def navigate():
    """
    route to navigate between two points on the map
    the GET request must contain the following arguments:
    {
        source: <String>,
        dest: <String>,
        map_id: <String>
    }
    where source, dest are the names of the source and dest in the map, and map_id is the ID of the map
    """
    try:
        source = request.headers.get("source")
        dest = request.headers.get("dest")
        map_id = request.headers.get("map_id")

        if not source or not dest or not map_id:
            return jsonify({"error": "incomplete_form"}), 400

        map_ref = maps_ref.document(map_id)
        map = map_ref.get()
        if not map.exists:
            return jsonify({"error": "map_not_found"}), 404

        map = map.to_dict()
        if source not in map["nodes"] or dest not in map["nodes"]:
            return jsonify({"error": "invalid_node"}), 400

        result = functions.dijkistra(map, source, dest)

        return jsonify({"success": True, "path": result[1], "dist": result[0]}), 200
    except Exception as e:
        return f"An error occured: {e}", 500
