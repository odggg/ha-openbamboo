"""Subprocess fixture: exercises real pipes/threading without a printer."""
import json
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

def emit(value):
    print(json.dumps(value), flush=True)

serial = ""
for line in sys.stdin:
    request = json.loads(line)
    method, params = request["method"], request["params"]
    if method == "init":
        if mode == "cloudcheck":
            assert params["local"] is False
            assert params["username"] == "u_12345"
            assert params["password"] == "account-token"
            assert "access_code" not in params
        serial = params["serial"]
        emit({"id": request["id"], "rc": 0})
        emit({"event": "connected"})
        emit({"event": "capabilities", "signed_ready": mode == "signed"})
        if mode == "eof":
            sys.exit(0)
    elif method == "camera_start":
        emit({"id": request["id"], "rc": 0})
        if mode == "camera":
            from io import BytesIO
            import base64
            from PIL import Image
            image = BytesIO()
            Image.new("RGB", (64, 48), "blue").save(image, "JPEG")
            emit({"event": "camera_state", "serial": serial, "state": "connecting"})
            # A foreign printer frame must never be shown.
            emit({"event": "camera_frame", "serial": "OTHER", "codec": "mjpeg",
                  "data": base64.b64encode(image.getvalue()).decode()})
            emit({"event": "camera_frame", "serial": serial, "codec": "mjpeg",
                  "data": base64.b64encode(image.getvalue()).decode()})
        else:
            emit({"event": "camera_state", "serial": serial,
                  "state": "missing_signing_credentials"})
    elif method == "publish":
        if mode == "hang":
            time.sleep(2)
            continue
        emit({"id": request["id"], "rc": -26 if mode == "reject" else 0})
        emit({"event": "message", "serial": serial, "payload": params["payload"]})
