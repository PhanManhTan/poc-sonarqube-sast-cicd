"""Intentionally vulnerable Flask examples for SAST validation only.

Do not import, execute, or copy this module into an application.
"""

import sqlite3
import subprocess

from flask import Flask, jsonify, request, send_file


app = Flask(__name__)
app.config["SECRET_KEY"] = "poc-only-hard-coded-secret"


@app.get("/sast-fixture/users")
def unsafe_user_lookup():
    username = request.args.get("username", "")
    with sqlite3.connect(":memory:") as database:
        query = f"SELECT id, username FROM users WHERE username = '{username}'"
        rows = database.execute(query).fetchall()
    return jsonify(rows)


@app.get("/sast-fixture/ping")
def unsafe_ping():
    host = request.args.get("host", "localhost")
    command = f"ping -c 1 {host}"
    result = subprocess.run(
        command,
        shell=True,
        check=False,
        capture_output=True,
        text=True,
    )
    return {"output": result.stdout}


@app.get("/sast-fixture/download")
def unsafe_download():
    return send_file(request.args.get("path", "report.txt"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
