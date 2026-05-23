# Welcome to MediScan AI

**AI-Powered MRI Segmentation for Brain, Cardiac & Prostate Imaging**  
*Using DeepLabV3+ with ResNet-50 — achieving Dice scores up to 0.9935*

---

## Here's What You're Working With

This project has a pretty straightforward layout. Here's the tour:

```
mediscan_flask/
├── app.py                          ← This launches everything
├── requirements.txt                ← All the Python stuff you'll need
├── models/                         ← ⚠️ Your trained models go here
│   ├── deeplabv3plus_baseline_brain.keras
│   ├── deeplabv3plus_baseline.keras          (the heart one)
│   └── deeplabv3plus_baseline_prostate_best.keras
├── inference/
│   ├── __init__.py
│   ├── brain_inference.py          ← Does brain segmentation
│   ├── heart_inference.py          ← Does cardiac segmentation
│   └── prostate_inference.py       ← Does prostate segmentation
└── static/
    ├── index.html                  ← The user interface
    ├── style.css                   ← Makes it look pretty
    └── script.js                   ← Connects the front end to the backend
```

---

## STEP 1 — Get Your Model Files (This is crucial!)

Your three trained models are sitting on Google Drive, and they need to move into your `models/` folder. This is probably the most important step, so let's get it right.

| Organ    | Where it is on Drive | What to name it in `models/` |
|----------|----------------------|-----|
| Brain    | `brain_segmentation_models_nifti/deeplabv3plus_baseline_brain.keras` | `deeplabv3plus_baseline_brain.keras` |
| Heart    | `models-20260405T173917Z-1-001/models/deeplabv3plus_baseline.keras` | `deeplabv3plus_baseline.keras` |
| Prostate | `prostate_segmentation_model/deeplabv3plus_baseline_prostate_best.keras` | `deeplabv3plus_baseline_prostate_best.keras` |

**Quick walkthrough:**
1. Head to [drive.google.com](https://drive.google.com)
2. Find each folder from the table above
3. Right-click the `.keras` file → **Download** it
4. Drag it into your `mediscan_flask/models/` folder

Once you're done, your `models/` folder should look like this:
```
mediscan_flask/models/
├── deeplabv3plus_baseline_brain.keras
├── deeplabv3plus_baseline.keras
└── deeplabv3plus_baseline_prostate_best.keras
```

That's it for step 1. Everything else builds on this.

---

## STEP 2 — Set Up a Virtual Environment

A virtual environment is like a sandbox just for this project. It keeps things clean and prevents conflicts with other Python stuff on your computer.

Open your terminal (or command prompt on Windows) and navigate to the `mediscan_flask/` folder, then run:

### On Windows
```cmd
python -m venv venv
venv\Scripts\activate
```

### On macOS or Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

You'll know it worked when you see `(venv)` at the beginning of your terminal prompt. Cool, right?

---

## STEP 3 — Install Everything You Need

Now let's grab all the dependencies. This is simple:

```bash
pip install -r requirements.txt
```

This downloads and installs:
- **Flask** — the web server that serves your app
- **TensorFlow** — the heavy lifter that runs your AI models
- **OpenCV** — handles image manipulation and visualizations
- **NumPy** — does all the math with arrays
- **nibabel** — lets you work with NIfTI brain scan files (`.nii.gz`)
- **Pillow** — converts images to formats the web can handle

**Pro tips:**
- If you've got an NVIDIA GPU with CUDA installed, TensorFlow will automatically use it—your predictions will be way faster.
- TensorFlow is pretty large (~500 MB), so don't freak out if the install takes a minute or two. It's normal.

---

## STEP 4 — Fire Up the Server

Ready to start? Just run:

```bash
python app.py
```

If everything's set up right, you'll see something like this:

```
============================================================
  MediScan AI — Flask Server
============================================================
  Static files : /path/to/mediscan_flask/static
  Models dir   : /path/to/mediscan_flask/models
  brain      → deeplabv3plus_baseline_brain.keras  ✅
  heart      → deeplabv3plus_baseline.keras         ✅
  prostate   → deeplabv3plus_baseline_prostate_best.keras  ✅
============================================================
  Open Chrome at:  http://127.0.0.1:5000
============================================================
```

All green checkmarks? You're golden.

**If a model shows `NOT FOUND`:** Go back to Step 1 and double-check the filenames. They need to be *exactly* right. Restart the server after you fix it.

---

## STEP 5 — Open It Up in Your Browser

Launch Google Chrome and head to:

```
http://127.0.0.1:5000
```

The interface will load right up. Here's a heads-up though: the first time you run a prediction for each organ, it might take 5–15 seconds while TensorFlow loads the model into memory. Don't worry—after that, predictions are super fast (1–3 seconds).

---

## STEP 6 — Actually Use It

Here's the flow:

1. **Sign up or log in** — create an account (it's stored locally in your browser, so it's all you)
2. **Upload an MRI image** — drag and drop or click to browse for a PNG/JPEG file
3. **Pick the organ** — Brain / Heart / Prostate (or let it auto-detect)
4. **Choose your model** — DeepLabV3+ Baseline (your trained model)
5. **Hit "Analyze MRI"** — watch the progress bar as the model works its magic
6. **Explore the results** — swap between Overlay, Mask, and Heatmap views
7. **Check the report** — see your original MRI, the AI's prediction, the overlay, and a heatmap all side by side

---

## API Endpoints — If You're Building Something Custom

If you want to integrate this into another app or use it programmatically, here are the endpoints:

| Method | Where | What it does |
|--------|-------|-------|
| `GET`  | `/` | Loads up the web interface |
| `GET`  | `/health` | Checks if the server's alive and shows which models are loaded |
| `GET`  | `/model_status` | Tells you which model files exist and if they're ready to go |
| `POST` | `/predict` | **The main event** — runs the AI segmentation |

### Sending a Prediction Request (POST `/predict`)

You'll send:

| Field | Type | Options |
|-------|------|---------|
| `file` | A file | PNG, JPEG, or NIfTI format (.nii.gz) |
| `organ` | Text | `brain`, `heart`, `prostate`, or `auto` (to auto-detect) |
| `model` | Text | `deeplabv3_baseline` |

### What You Get Back

The server responds with JSON that looks like this:

```json
{
  "success": true,
  "metrics": {
    "organ": "Brain",
    "model": "DeepLabV3+ Baseline (Brain)",
    "dice": 0.9914,
    "iou": 0.9714,
    "confidence": 87.3,
    "affected_pct": 5.2,
    "volume_cc": 0.416,
    "risk_level": "MEDIUM",
    "label": "Moderate Tumor Presence",
    "recommendations": ["Follow-up MRI within 4–6 weeks...", "..."],
    "detected": true,
    "proc_time_s": 1.34
  },
  "images": {
    "original": "<base64 PNG>",
    "mask":     "<base64 PNG>",
    "overlay":  "<base64 PNG>",
    "heatmap":  "<base64 PNG>"
  }
}
```

---

## Stuck? Here's Help

### "Model file not found" (error in the browser)
- The `.keras` file isn't where it should be
- Check that the filename matches the table in Step 1 *exactly*
- Restart the server after you move the file

### `ModuleNotFoundError: No module named 'tensorflow'`
- Make sure you activated your virtual environment (you should see `(venv)` in your prompt)
- Run `pip install -r requirements.txt` again

### `Address already in use` (port 5000)
- Something else is using port 5000
- Edit `app.py` and change `app.run(port=5001)` instead
- Then visit `http://127.0.0.1:5001`

### Predictions are really slow the first time
- Totally normal! TensorFlow is loading. Be patient.
- After that first run, you're in the clear—predictions will be quick.

### `InvalidArgumentError` when making a prediction
- Your image might be corrupted or in a format we don't support
- Try exporting a fresh PNG or JPEG from your DICOM viewer

### NIfTI files aren't working (`.nii.gz`)
- Make sure `nibabel` is installed: `pip install nibabel`
- Also, NIfTI only works for brain scans right now

### "flask-cors not found"
- Quick fix:
```bash
pip install flask-cors
```

---

## What You'll Need

| What | Bare Minimum | Sweet Spot |
|------|-------------|-----------|
| Python | 3.9 | 3.10 or 3.11 |
| RAM | 4 GB | 8 GB or more |
| GPU | Not needed | NVIDIA with CUDA (way faster) |
| OS | Windows 10 / macOS 12 / Ubuntu 20.04 | Any modern OS |
| Browser | Chrome 90 | Latest Chrome |

---

## Your Privacy Matters

Everything happens on your computer. Your MRI images, patient data, all of it—stays local. Nothing gets sent anywhere else. You have full control.

---

## Important Legal Stuff

This tool is built for learning, research, and experimentation. It's **not** a medical device and doesn't provide clinical diagnosis, treatment plans, or medical advice. If you or someone else needs medical care, please talk to a real doctor. Always.
