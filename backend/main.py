import os
import sys
import types
from pathlib import Path
import io
import json
import base64
import logging
import time
import hmac
import hashlib
import sqlite3
from typing import Optional

# ==========================================================
# ENVIRONMENT & COMPATIBILITY SHIMS
# ==========================================================

BASE_DIR = Path(__file__).resolve().parent

os.environ.setdefault("KERAS_HOME", str(BASE_DIR / ".keras"))
os.environ.setdefault("MPLCONFIGDIR", str(BASE_DIR / ".matplotlib"))
os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")

# Protobuf 4.x / 5.x runtime_version stub compatibility
try:
    import google.protobuf.runtime_version
except ImportError:
    m = types.ModuleType("google.protobuf.runtime_version")
    m.Domain = type("Domain", (), {"PUBLIC": 1, "INTERNAL": 2})
    m.ValidateProtobufRuntimeVersion = lambda *a, **k: None
    sys.modules["google.protobuf.runtime_version"] = m

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.cm as cm
from fastapi import FastAPI, UploadFile, File, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError
import tensorflow as tf
from tensorflow import keras

# Patch Keras Dense deserialization for saved quantization_config attribute
def _patched_dense_from_config(cls, config):
    c = dict(config)
    c.pop("quantization_config", None)
    return super(keras.layers.Dense, cls).from_config(c)

keras.layers.Dense.from_config = classmethod(_patched_dense_from_config)

# ==========================================================
# LOGGING
# ==========================================================

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================================
# FASTAPI APPLICATION
# ==========================================================

app = FastAPI(
    title="Diabetic Retinopathy Detection API",
    description=(
        "API for AI-assisted diabetic retinopathy image "
        "classification with Grad-CAM visual explainability. "
        "Predictions are not medical diagnoses."
    ),
    version="1.2.0",
)

# ==========================================================
# CORS
# ==========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "*",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# PATHS & CONFIG
# ==========================================================

MODEL_PATH = BASE_DIR / "disease_detection_model.keras"
CLASS_NAMES_PATH = BASE_DIR / "class_names.json"
METRICS_PATH = BASE_DIR / "test_metrics.json"

MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB

# ==========================================================
# JWT CONFIGURATION & AUTHENTICATION STORE
# ==========================================================

JWT_SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY", "m16bQVT1S7PenuyidaC2VV9HLRdMW0cdfvFjL4Tmhj8"
)
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRATION_SECONDS = int(os.environ.get("JWT_EXPIRATION_DAYS", 7)) * 24 * 3600
DB_PATH = BASE_DIR / "users.db"


def init_user_db():
    """Initializes SQLite user credentials store with demo account."""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()

        # Seed demo medical practitioner account if absent
        cursor.execute("SELECT id FROM users WHERE email = ?", ("doctor@retinascan.ai",))
        if not cursor.fetchone():
            demo_hash = hashlib.sha256("Password123".encode("utf-8")).hexdigest()
            cursor.execute(
                "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
                ("doctor@retinascan.ai", "Dr. Sarah Mitchell", demo_hash),
            )
            conn.commit()
            logger.info("Demo user doctor@retinascan.ai created in SQLite database.")
        conn.close()
    except Exception as exc:
        logger.warning("Could not initialize SQLite user database: %s", exc)


init_user_db()


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(s: str) -> bytes:
    pad = 4 - (len(s) % 4)
    if pad != 4:
        s += "=" * pad
    return base64.urlsafe_b64decode(s.encode("utf-8"))


def create_jwt_token(payload: dict, expires_in: int = JWT_EXPIRATION_SECONDS) -> str:
    """Generates an RFC 7519 compliant HS256 JWT using the secret key."""
    now = int(time.time())
    data = dict(payload)
    data.setdefault("iat", now)
    data.setdefault("exp", now + expires_in)

    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    h_b64 = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    b_b64 = _b64url_encode(json.dumps(data, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{h_b64}.{b_b64}".encode("utf-8")
    sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    s_b64 = _b64url_encode(sig)
    return f"{h_b64}.{b_b64}.{s_b64}"


def verify_jwt_token(token: str) -> dict:
    """Verifies HS256 JWT signature and validity against the secret key."""
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT token format (expected 3 parts)")
    h_b64, b_b64, s_b64 = parts
    signing_input = f"{h_b64}.{b_b64}".encode("utf-8")
    expected_sig = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(s_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("JWT signature verification failed")
    payload = json.loads(_b64url_decode(b_b64).decode("utf-8"))
    if "exp" in payload and int(time.time()) > payload["exp"]:
        raise ValueError("JWT token has expired")
    return payload

# Metadata mapping for classes
CLASS_METADATA = {
    "No_DR": {
        "level": 0,
        "label": "No Diabetic Retinopathy",
        "color": "#2f9e6b",
        "advice": "No signs detected. Continue yearly eye screening and keep blood sugar controlled.",
    },
    "Mild": {
        "level": 1,
        "label": "Mild (NPDR)",
        "color": "#9bb52f",
        "advice": "Early microaneurysms detected. Review with an eye doctor within 6–12 months and manage glucose, BP and cholesterol.",
    },
    "Moderate": {
        "level": 2,
        "label": "Moderate (NPDR)",
        "color": "#e0a526",
        "advice": "Noticeable retinal changes, hemorrhages, or exudates. Book an ophthalmologist visit within 3–6 months.",
    },
    "Severe": {
        "level": 3,
        "label": "Severe (NPDR)",
        "color": "#e0692a",
        "advice": "High risk of rapid progression. See a retina specialist promptly (within weeks) for fluorescein angiography.",
    },
    "Proliferate_DR": {
        "level": 4,
        "label": "Proliferative DR",
        "color": "#cf3a3a",
        "advice": "Most advanced stage with neovascularization. Urgent specialist evaluation is needed (within days) to prevent vision loss.",
    },
}

# ==========================================================
# LOAD THE SAVED KERAS MODEL
# ==========================================================

def load_retinopathy_model():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"Trained Keras model not found: {MODEL_PATH}"
        )

    try:
        loaded_model = keras.models.load_model(
            MODEL_PATH,
            compile=False,
        )

        if not loaded_model.built:
            raise RuntimeError("The loaded model is not built.")

        logger.info("Trained Keras model loaded successfully.")
        logger.info("Model path: %s", MODEL_PATH)
        logger.info("Input shape: %s", loaded_model.input_shape)
        logger.info("Output shape: %s", loaded_model.output_shape)

        return loaded_model

    except Exception as exc:
        logger.exception("Failed to load the trained Keras model.")
        raise RuntimeError(
            "Unable to load disease_detection_model.keras. "
            "Check the TensorFlow/Keras environment and model file."
        ) from exc


model = load_retinopathy_model()

# ==========================================================
# VALIDATE MODEL INPUT AND OUTPUT SHAPES
# ==========================================================

if len(model.input_shape) != 4:
    raise RuntimeError(f"Expected a 4D image input; got {model.input_shape}")

if model.input_shape[-1] != 3:
    raise RuntimeError(f"Expected RGB input; got {model.input_shape}")

if model.input_shape[1] is None or model.input_shape[2] is None:
    raise RuntimeError("The model must have fixed image height and width.")

IMAGE_SIZE = (
    int(model.input_shape[1]),
    int(model.input_shape[2]),
)

if len(model.output_shape) != 2:
    raise RuntimeError(f"Expected a 2D classification output; got {model.output_shape}")

NUM_CLASSES = int(model.output_shape[-1])
logger.info("Inference image size: %s", IMAGE_SIZE)
logger.info("Number of model output classes: %d", NUM_CLASSES)

# ==========================================================
# GRAD-CAM SUBMODEL SETUP
# ==========================================================

eff_submodel = None
try:
    eff_layer = model.get_layer("efficientnetb0")
    top_conv_layer = eff_layer.get_layer("top_conv")
    eff_submodel = keras.Model(
        inputs=eff_layer.inputs,
        outputs=[top_conv_layer.output, eff_layer.output],
    )
    logger.info("Grad-CAM submodel initialized with layer 'top_conv'.")
except Exception as e:
    logger.warning("Could not initialize Grad-CAM submodel: %s", e)

# ==========================================================
# CLASS LABELS
# ==========================================================

DEFAULT_CLASS_NAMES = [
    "Mild",
    "Moderate",
    "No_DR",
    "Proliferate_DR",
    "Severe",
]

def load_class_names():
    if CLASS_NAMES_PATH.is_file():
        with CLASS_NAMES_PATH.open("r", encoding="utf-8") as file:
            names = json.load(file)

        if not isinstance(names, list) or len(names) != NUM_CLASSES:
            raise RuntimeError(
                f"class_names.json must match {NUM_CLASSES} outputs."
            )
        return names

    return DEFAULT_CLASS_NAMES

CLASS_NAMES = load_class_names()

# ==========================================================
# EVALUATION METRICS
# ==========================================================

def load_evaluation_metrics():
    if not METRICS_PATH.is_file():
        return None
    try:
        with METRICS_PATH.open("r", encoding="utf-8") as file:
            metrics = json.load(file)
        accuracy = metrics.get("test_accuracy_percent")
        return float(accuracy) if accuracy is not None else None
    except Exception:
        return None

TEST_ACCURACY = load_evaluation_metrics()

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/jpg",
}

# ==========================================================
# HEALTH & MODEL INFO ENDPOINTS
# ==========================================================

@app.get("/")
def home():
    return {
        "message": "Diabetic Retinopathy API with Grad-CAM is running",
        "model_loaded": model is not None,
        "input_image_size": list(IMAGE_SIZE),
        "number_of_classes": NUM_CLASSES,
        "test_accuracy_percent": TEST_ACCURACY,
        "features": ["classification", "gradcam_explainability", "class_probabilities"],
    }

@app.get("/model-info")
def model_info():
    return {
        "model_name": "Diabetic Retinopathy EfficientNet Classifier",
        "input_image_size": list(IMAGE_SIZE),
        "number_of_classes": NUM_CLASSES,
        "class_names": CLASS_NAMES,
        "class_metadata": CLASS_METADATA,
        "test_accuracy_percent": TEST_ACCURACY,
        "gradcam_supported": eff_submodel is not None,
    }

# ==========================================================
# IMAGE PREPROCESSING
# ==========================================================

def preprocess_image(contents: bytes) -> np.ndarray:
    try:
        with Image.open(io.BytesIO(contents)) as uploaded_image:
            if uploaded_image.format not in {"JPEG", "PNG"}:
                raise HTTPException(
                    status_code=400,
                    detail="Please upload a valid JPG or PNG image.",
                )

            image = uploaded_image.convert("RGB")
            image = image.resize(
                (IMAGE_SIZE[1], IMAGE_SIZE[0]),
                Image.Resampling.BILINEAR,
            )
            image_array = np.asarray(image, dtype=np.float32)

    except HTTPException:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is not a valid image.",
        ) from exc

    return np.expand_dims(image_array, axis=0)

# ==========================================================
# GRAD-CAM GENERATION (EXPLAINABLE AI)
# ==========================================================

def generate_gradcam(image_array: np.ndarray, original_bytes: bytes, target_class_idx: int):
    """
    Computes Grad-CAM heatmap highlighting regions contributing
    to the predicted diabetic retinopathy grade.
    Returns base64 data URLs for:
    - heatmap_overlay: original image with heatmap blended on top
    - heatmap_raw: colored heatmap mask
    """
    if eff_submodel is None:
        return None

    try:
        # Run forward pass through the sequential head with GradientTape
        with tf.GradientTape() as tape:
            aug_out = model.get_layer("augmentation")(image_array, training=False)
            conv_features, eff_out = eff_submodel(aug_out, training=False)
            tape.watch(conv_features)

            x = model.get_layer("global_average_pooling2d_1")(eff_out)
            x = model.get_layer("batch_normalization_1")(x, training=False)
            x = model.get_layer("dropout_2")(x, training=False)
            x = model.get_layer("dense_1")(x)
            x = model.get_layer("dropout_3")(x, training=False)
            preds = model.get_layer("disease_classes")(x)

            loss = preds[:, target_class_idx]

        # Gradients of predicted class wrt top_conv feature maps
        grads = tape.gradient(loss, conv_features)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

        # Weight feature maps by pooled gradients
        heatmap = tf.reduce_sum(tf.multiply(pooled_grads, conv_features[0]), axis=-1)
        heatmap = tf.maximum(heatmap, 0).numpy()

        # Normalize between 0 and 1
        max_val = np.max(heatmap)
        if max_val > 0:
            heatmap = heatmap / max_val
        else:
            heatmap = np.zeros_like(heatmap)

        # Convert to colormap (JET)
        colormap = matplotlib.colormaps["jet"]
        colored_heatmap = colormap(heatmap)[:, :, :3]  # RGB in [0, 1]
        colored_heatmap_uint8 = (colored_heatmap * 255).astype(np.uint8)

        # Open original image to blend at exact original dimensions
        with Image.open(io.BytesIO(original_bytes)) as orig:
            orig_rgb = orig.convert("RGB")
            orig_w, orig_h = orig_rgb.size

            # Resize colored heatmap to match original image dimensions
            heatmap_img = Image.fromarray(colored_heatmap_uint8).resize(
                (orig_w, orig_h), Image.Resampling.BILINEAR
            )

            # Create alpha blended overlay (60% original image + 40% heatmap)
            blended = Image.blend(orig_rgb, heatmap_img, alpha=0.42)

            # Encode blended image to PNG base64
            overlay_buf = io.BytesIO()
            blended.save(overlay_buf, format="PNG")
            overlay_b64 = base64.b64encode(overlay_buf.getvalue()).decode("utf-8")

            # Encode raw heatmap to PNG base64
            raw_buf = io.BytesIO()
            heatmap_img.save(raw_buf, format="PNG")
            raw_b64 = base64.b64encode(raw_buf.getvalue()).decode("utf-8")

            return {
                "heatmap_overlay": f"data:image/png;base64,{overlay_b64}",
                "heatmap_raw": f"data:image/png;base64,{raw_b64}",
                "target_class": CLASS_NAMES[target_class_idx],
            }

    except Exception as exc:
        logger.exception("Failed to generate Grad-CAM heatmap: %s", exc)
        return None

# ==========================================================
# AUTHENTICATION ENDPOINTS (JWT)
# ==========================================================

@app.post("/auth/register")
async def register(request: Request):
    """
    Registers a new user into SQLite database and returns
    an HS256 JWT access token signed with the configured secret key.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    name = (data.get("name") or "").strip() or email.split("@")[0]

    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email address is required.")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters.")

    pwd_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (email,))
        if cursor.fetchone():
            conn.close()
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists. Please log in.",
            )

        cursor.execute(
            "INSERT INTO users (email, name, password_hash) VALUES (?, ?, ?)",
            (email, name, pwd_hash),
        )
        conn.commit()
        conn.close()
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Failed to insert user into SQLite")
        raise HTTPException(status_code=500, detail="Failed to register account.") from exc

    token = create_jwt_token({"email": email, "name": name})
    return {
        "token": token,
        "token_type": "Bearer",
        "user": {"email": email, "name": name},
        "message": "Account created successfully.",
    }


@app.post("/auth/login")
async def login(request: Request):
    """
    Authenticates user credentials against SQLite and returns
    an HS256 JWT access token signed with the configured secret key.
    """
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        raise HTTPException(status_code=400, detail="Email and password are required.")

    pwd_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()

    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("SELECT name, password_hash FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(
                status_code=401,
                detail="No account found with this email. Please check your email or register.",
            )

        user_name, stored_hash = row
        if stored_hash != pwd_hash:
            raise HTTPException(status_code=401, detail="Incorrect password.")

        token = create_jwt_token({"email": email, "name": user_name})
        return {
            "token": token,
            "token_type": "Bearer",
            "user": {"email": email, "name": user_name},
            "message": "Login successful.",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Login database query failed")
        raise HTTPException(status_code=500, detail="Login service error.") from exc


@app.get("/auth/me")
def get_current_user(authorization: Optional[str] = Header(None)):
    """Verifies Bearer JWT token against the configured secret key."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header.")
    token = authorization.split("Bearer ")[1].strip()
    try:
        payload = verify_jwt_token(token)
        return {"authenticated": True, "user": payload}
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


# ==========================================================
# PREDICTION ENDPOINT
# ==========================================================

@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None),
):
    authenticated_user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ")[1].strip()
        try:
            authenticated_user = verify_jwt_token(token)
            logger.info(
                "Diagnostic screening requested by authenticated doctor: %s (%s)",
                authenticated_user.get("name"),
                authenticated_user.get("email"),
            )
        except Exception as auth_err:
            logger.warning("Optional JWT token verification warning: %s", auth_err)

    try:
        if file.content_type not in ALLOWED_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Please upload a JPG or PNG image.",
            )

        contents = await file.read(MAX_UPLOAD_BYTES + 1)

        if not contents:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        if len(contents) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Image exceeds the 10 MB upload limit.",
            )

        image_array = preprocess_image(contents)

        raw_output = np.asarray(model.predict(image_array, verbose=0))

        if raw_output.shape != (1, NUM_CLASSES):
            raise RuntimeError(
                f"Unexpected model output shape: {raw_output.shape}"
            )

        scores = raw_output[0]

        if not np.all(np.isfinite(scores)):
            raise RuntimeError("The model returned NaN or infinite values.")

        predicted_index = int(np.argmax(scores))
        predicted_class = CLASS_NAMES[predicted_index]
        confidence = float(scores[predicted_index] * 100)

        # Feature 2: All 5 Classes Probability Distribution
        probabilities = []
        for i in range(NUM_CLASSES):
            c_name = CLASS_NAMES[i]
            meta = CLASS_METADATA.get(c_name, {
                "level": i,
                "label": c_name,
                "color": "#0f6e73",
                "advice": "",
            })
            probabilities.append({
                "class_name": c_name,
                "label": meta["label"],
                "level": meta["level"],
                "color": meta["color"],
                "probability_percent": round(float(scores[i] * 100), 2),
                "is_predicted": (i == predicted_index),
            })

        # Sort probabilities by clinical severity level (0 to 4)
        probabilities.sort(key=lambda item: item["level"])

        # Feature 1: Grad-CAM Explainable AI Visual Heatmap
        gradcam_result = generate_gradcam(image_array, contents, predicted_index)

        logger.info(
            "Prediction completed: class=%s index=%d confidence=%.2f%% gradcam=%s",
            predicted_class,
            predicted_index,
            confidence,
            gradcam_result is not None,
        )

        return {
            "predicted_class": predicted_class,
            "confidence_percent": round(confidence, 2),
            "model_validation_accuracy_percent": (
                f"{TEST_ACCURACY:.2f}" if TEST_ACCURACY is not None else None
            ),
            "probabilities": probabilities,
            "gradcam": gradcam_result,
            "message": "AI prediction only; this is not a medical diagnosis.",
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Prediction failed.")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Check the backend logs.",
        ) from exc
    finally:
        await file.close()
