from flask import Flask, render_template, request, jsonify
import logging
import json
import random

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

filename = "bm.json"

with open(filename, encoding="utf-8") as f:
    data = json.load(f)

@app.route("/")
def serve_website():
    return render_template("main.html")

@app.route("/get_data")
def get_data():
    unlabeled_data = [(i, x) for i, x in enumerate(data) if "label" not in x]
    picked_data = random.choice(unlabeled_data)
    send_data = {
        "id": picked_data[0],
        "cat": picked_data[1]["cat"],
        "title": picked_data[1]["title"],
        "content": (picked_data[1]["desc"] + " " if picked_data[1]["desc"] != "" else "") + picked_data[1]["detail"],
        "url": picked_data[1]["url"],
        "remain": f"{len(unlabeled_data)}/{len(data)}"
    }
    return jsonify(send_data)

@app.route("/submit", methods=["POST"])
def submit():
    id = request.form["id"]
    label = request.form["label"]
    data[int(id)]["label"] = label
    app.logger.info(f"{id} is {label}")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    return "OK"

    # return jsonify({"id": request.form["id"], "label": request.form["label"]})