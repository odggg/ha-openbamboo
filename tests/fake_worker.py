"""Subprocess fixture: exercises real pipes/threading without a printer."""
import json
import sys
import time

mode = sys.argv[1] if len(sys.argv) > 1 else "normal"

def emit(value):
    print(json.dumps(value), flush=True)

serial = ""
sequence = 20000
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
        body = json.loads(params["payload"])
        reply = {"id": request["id"], "rc": -26 if mode == "reject" else 0}
        if isinstance(body.get("print"), dict) and "command" in body["print"]:
            sequence = 20000 + ((sequence - 20000 + 1) % 10000)
            body["print"]["sequence_id"] = str(sequence)
            reply["sequence_id"] = str(sequence)
            if mode == "firmware_reject":
                # The firmware reply may precede the native publish response.
                emit({"event": "message", "serial": serial, "payload": json.dumps({
                    "print": {"command": body["print"]["command"],
                              "sequence_id": str(sequence), "err_code": 84033544,
                              "result": "fail", "reason": "private text must not escape"}})})
        emit(reply)
        emit({"event": "message", "serial": serial, "payload": json.dumps(body)})
