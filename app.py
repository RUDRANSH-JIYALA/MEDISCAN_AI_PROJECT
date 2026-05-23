"""
app.py — MediScan AI Flask Server
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "mediscan_flask"))

import base64
import cv2
import logging
import time
from pathlib import Path
import numpy as np   # ✅ added

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(levelname)s]  %(message)s",
)
log = logging.getLogger(__name__)

# ── App setup ─────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
MODELS_DIR = BASE_DIR / "models"

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="")
CORS(app)

# ── Inference modules ─────────────────────────────────────────────────────────
import inference.brain_inference    as brain_mod
import inference.heart_inference    as heart_mod
import inference.prostate_inference as prostate_mod
from inference.organ_detector import detect_organ
from inference.chart_utils    import make_contour_png, make_prob_map_png, make_chart_data

# ─────────────────────────────────────────────────────────────────────────────
# ✅ FIX: JSON-safe conversion
# ─────────────────────────────────────────────────────────────────────────────
def convert_types(obj):
    if isinstance(obj, dict):
        return {k: convert_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_types(i) for i in obj]
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        return float(obj)
    else:
        return obj


# ─────────────────────────────────────────────────────────────────────────────
# Medical image validator
# ─────────────────────────────────────────────────────────────────────────────

def _validate_medical_image(file_bytes: bytes, filename: str) -> dict:
    """
    Basic check: reject images that are clearly NOT medical MRI scans.

    MRI scans are always grayscale — they have no color saturation.
    Color photographs (food, nature, etc.) have high HSV saturation.

    Returns {"valid": True} or {"valid": False, "reason": str}
    """
    # NIfTI files bypass this check — they are always medical data
    if filename.lower().endswith((".nii", ".nii.gz", ".dcm")):
        return {"valid": True}

    arr     = np.frombuffer(file_bytes, dtype=np.uint8)
    img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img_bgr is None:
        return {"valid": False, "reason": "Could not decode image file."}

    # ─ Color saturation check ─────────────────────────────────────────
    # HSV Saturation channel: 0→no color, 255→fully saturated color
    # MRI scans: mean saturation < 15  (essentially grayscale)
    # Color photos (apple, food): mean saturation typically > 40
    img_hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
    mean_sat = float(img_hsv[:, :, 1].mean())
    if mean_sat > 25:
        return {
            "valid": False,
            "reason": (
                f"Image appears to be a color photograph, not a medical MRI scan "
                f"(color saturation {mean_sat:.0f}/255 — MRI scans are always grayscale). "
                f"Please upload a real MRI scan (PNG/JPEG/NIfTI)."
            ),
        }

    # ─ Minimum size check ──────────────────────────────────────────
    h, w = img_bgr.shape[:2]
    if h < 32 or w < 32:
        return {"valid": False, "reason": f"Image too small ({w}×{h}px). Minimum 32×32px."}

    return {"valid": True}


# ─────────────────────────────────────────────────────────────────────────────
# Model paths
# ─────────────────────────────────────────────────────────────────────────────
MODEL_PATHS = {
    "brain":    str(MODELS_DIR / "deeplabv3plus_baseline_brain.keras"),
    "heart":    str(MODELS_DIR / "deeplabv3plus_baseline.keras"),
    "prostate": str(MODELS_DIR / "deeplabv3plus_baseline_prostate_best.keras"),
}

_loaded = {"brain": False, "heart": False, "prostate": False}


def _load_model(organ: str) -> bool:
    if _loaded[organ]:
        return True
    path = MODEL_PATHS[organ]
    if not os.path.exists(path):
        log.error(f"Model file not found: {path}")
        return False
    try:
        if organ == "brain":
            brain_mod.load_model(path)
        elif organ == "heart":
            heart_mod.load_model(path)
        elif organ == "prostate":
            prostate_mod.load_model(path)
        _loaded[organ] = True
        log.info(f"[{organ}] model loaded ✅")
        return True
    except Exception as exc:
        log.exception(f"Failed to load {organ} model: {exc}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(str(STATIC_DIR), "index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok", "models_loaded": _loaded})


@app.route("/detect_organ", methods=["POST"])
def detect_organ_route():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    file_bytes = f.read()
    result     = detect_organ(file_bytes, f.filename or "")
    result     = convert_types(result)   # ✅ FIX
    return jsonify(result)


@app.route("/predict", methods=["POST"])
def predict():

    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file uploaded"}), 400

    file  = request.files["file"]
    organ = request.form.get("organ", "auto").lower().strip()

    if file.filename == "":
        return jsonify({"success": False, "error": "Empty filename"}), 400

    file_bytes = file.read()
    filename   = file.filename or ""
    detected_method = None

    # ── Image validity check ─────────────────────────────────────────────
    validation = _validate_medical_image(file_bytes, filename)
    if not validation["valid"]:
        return jsonify({"success": False, "error": validation["reason"]}), 400

    # ── Organ detection ───────────────────────────────────────────────────────
    if organ == "auto":
        detection = detect_organ(file_bytes, filename)
        organ            = detection["organ"]
        detected_method  = detection["method"]

    if organ not in ("brain", "heart", "prostate"):
        return jsonify({"success": False, "error": f"Unknown organ: {organ}"}), 400

    # ── Load model ────────────────────────────────────────────────────────────
    if not _load_model(organ):
        return jsonify({"success": False, "error": "Model not found"}), 503

    # ── Run inference ─────────────────────────────────────────────
    t_start = time.time()   # ✔ record BEFORE inference
    try:
        if organ == "brain":
            result = brain_mod.predict(file_bytes, filename)
        elif organ == "heart":
            result = heart_mod.predict(file_bytes, filename)
        else:
            result = prostate_mod.predict(file_bytes, filename)
    except Exception as exc:
        log.exception("Inference error")
        return jsonify({"success": False, "error": str(exc)}), 500

    # Elapsed time in seconds (not a Unix timestamp)
    result["metrics"]["proc_time_s"] = round(float(time.time() - t_start), 3)

    # ── Generate extra images ────────────────────────────────────────────
    contour_png  = make_contour_png(result["original_png"], result["mask_png"], organ)
    prob_map_png = make_prob_map_png(result["heatmap_png"])

    # ── Chart data ──────────────────────────────────────────────────────
    chart_data = make_chart_data(
        result["original_png"],
        result["mask_png"],
        result["metrics"],
        organ,
    )

    # ── Encode images ───────────────────────────────────────────────────
    def b64(raw: bytes) -> str:
        return base64.b64encode(raw).decode("utf-8") if raw else ""

    response_body = {
        "success": True,
        "organ": organ,
        "metrics": result["metrics"],
        "chart_data": chart_data,
        "images": {
            "original": b64(result["original_png"]),
            "mask": b64(result["mask_png"]),
            "overlay": b64(result["overlay_png"]),
            "heatmap": b64(result["heatmap_png"]),
            "contour": b64(contour_png),
            "prob_map": b64(prob_map_png),
        },
    }

    if detected_method:
        response_body["detected_method"] = detected_method

    # ✅ FINAL FIX
    response_body = convert_types(response_body)

    return jsonify(response_body)


@app.route("/model_status")
def model_status():
    status = {}
    for organ, path in MODEL_PATHS.items():
        status[organ] = {
            "loaded": _loaded[organ],
            "path": path,
            "file_exists": os.path.exists(path),
        }
    status = convert_types(status)   # ✅ FIX
    return jsonify(status)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    log.info("MediScan AI running...")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)