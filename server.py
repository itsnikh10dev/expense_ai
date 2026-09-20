import re
import sqlite3
import threading
import uuid
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, request, send_from_directory

from ollama3 import response_to_user_query


# PATHS — identical to the original app.py

BASE_DIR = Path(__file__).resolve().parent
DB_NAME = BASE_DIR / "ocr_master.db"
TABLE_NAME = "ocr_line_items"
BILL_IMAGE_DIR = BASE_DIR / "bill_image"
CLEANED_IMAGE_DIR = BASE_DIR / "image_cleaning_one_folder"
EXTRACTED_TEXT_FILE = BASE_DIR / "extracted_text.txt"

ALLOWED_UPLOAD_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}


# DB HELPERS — copied verbatim from the original app.py.
# Same read-only guardrails, same behaviour.


def get_table_columns():
    """Return the actual columns of the table, or [] if the DB/table is missing."""
    if not DB_NAME.exists():
        return []
    try:
        con = sqlite3.connect(DB_NAME)
        cur = con.cursor()
        cur.execute(f"PRAGMA table_info({TABLE_NAME})")
        cols = [row[1] for row in cur.fetchall()]
        con.close()
        return cols
    except sqlite3.Error:
        return []


def run_query(sql_query, params=None):
    """Run a SELECT/PRAGMA query, returning (dataframe, error_message)."""
    if not DB_NAME.exists():
        return None, "Database not found yet. Upload and process a bill first."
    try:
        con = sqlite3.connect(DB_NAME)
        try:
            df = pd.read_sql_query(sql_query, con, params=params)
            return df, None
        finally:
            con.close()
    except sqlite3.OperationalError as e:
        return None, f"Database error: {e}"
    except Exception as e:
        return None, f"Unexpected error: {e}"


FORBIDDEN_SQL_KEYWORDS = [
    "DELETE", "UPDATE", "DROP", "ALTER", "INSERT", "TRUNCATE",
    "ATTACH", "DETACH", "REPLACE", "CREATE", "VACUUM",
]


def is_read_only_sql(sql_query):
    """Only allow read-only SELECT/PRAGMA/WITH queries with no mutating keywords."""
    if not sql_query or not sql_query.strip():
        return False
    normalized = sql_query.strip().upper()
    if not (normalized.startswith("SELECT") or normalized.startswith("PRAGMA") or normalized.startswith("WITH")):
        return False
    for word in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{word}\b", normalized):
            return False
    return True


def _df_to_records(df: pd.DataFrame):
    """NaN isn't valid JSON — swap for None before serializing."""
    return df.replace({np.nan: None}).to_dict(orient="records")



# APP

app = Flask(__name__, static_folder="static", static_url_path="")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# Dashboard — same aggregations as the Streamlit Dashboard page

@app.route("/api/dashboard")
def api_dashboard():
    columns = get_table_columns()
    if not columns:
        return jsonify({"has_data": False})

    df, err = run_query(f"SELECT * FROM {TABLE_NAME}")
    if err:
        return jsonify({"error": err}), 500
    if df.empty:
        return jsonify({"has_data": False})

    result = {"has_data": True, "total_records": len(df)}

    if "Invoice_No" in df.columns:
        result["total_invoices"] = int(df["Invoice_No"].nunique())
    if "Category" in df.columns:
        result["total_categories"] = int(df["Category"].nunique())
    if "Amount" in df.columns:
        amt = pd.to_numeric(df["Amount"], errors="coerce")
        result["total_amount"] = float(amt.sum()) if amt.notna().any() else None
        result["avg_amount"] = float(amt.mean()) if amt.notna().any() else None

    if "Category" in df.columns and "Amount" in df.columns:
        tmp = df.copy()
        tmp["Amount"] = pd.to_numeric(tmp["Amount"], errors="coerce")
        by_cat = tmp.dropna(subset=["Amount"]).groupby("Category")["Amount"].sum().sort_values(ascending=False)
        result["by_category"] = [{"category": str(k), "amount": float(v)} for k, v in by_cat.items()]

    if "Issue_Date" in df.columns and "Amount" in df.columns:
        tmp = df.copy()
        tmp["Issue_Date"] = pd.to_datetime(tmp["Issue_Date"], errors="coerce")
        tmp["Amount"] = pd.to_numeric(tmp["Amount"], errors="coerce")
        tmp = tmp.dropna(subset=["Issue_Date", "Amount"])
        if not tmp.empty:
            trend = tmp.groupby(tmp["Issue_Date"].dt.date)["Amount"].sum().sort_index()
            result["trend"] = [{"date": str(k), "amount": float(v)} for k, v in trend.items()]

    return jsonify(result)


# Expenses — same filtering behaviour as the Streamlit Expenses page,
# extended with search/date since the brief asked for them.

@app.route("/api/expenses/filters")
def api_expense_filters():
    columns = get_table_columns()
    if not columns:
        return jsonify({"categories": [], "invoices": [], "has_dates": False})
    df, err = run_query(f"SELECT * FROM {TABLE_NAME}")
    if err or df.empty:
        return jsonify({"categories": [], "invoices": [], "has_dates": False})
    categories = sorted([c for c in df["Category"].dropna().unique()]) if "Category" in df.columns else []
    invoices = sorted([str(i) for i in df["Invoice_No"].dropna().unique()]) if "Invoice_No" in df.columns else []
    return jsonify({
        "categories": categories,
        "invoices": invoices,
        "has_dates": "Issue_Date" in df.columns,
    })


@app.route("/api/expenses")
def api_expenses():
    columns = get_table_columns()
    if not columns:
        return jsonify({"has_data": False, "records": [], "columns": []})

    df, err = run_query(f"SELECT * FROM {TABLE_NAME}")
    if err:
        return jsonify({"error": err}), 500
    if df.empty:
        return jsonify({"has_data": True, "total": 0, "count": 0, "columns": list(df.columns), "records": []})

    filtered = df.copy()

    category = request.args.get("category")
    if category and "Category" in filtered.columns:
        cats = [c for c in category.split("|") if c]
        if cats:
            filtered = filtered[filtered["Category"].isin(cats)]

    invoice = request.args.get("invoice")
    if invoice and "Invoice_No" in filtered.columns:
        invs = [i for i in invoice.split("|") if i]
        if invs:
            filtered = filtered[filtered["Invoice_No"].astype(str).isin(invs)]

    date_from = request.args.get("date_from")
    date_to = request.args.get("date_to")
    if (date_from or date_to) and "Issue_Date" in filtered.columns:
        d = pd.to_datetime(filtered["Issue_Date"], errors="coerce")
        if date_from:
            filtered = filtered[d >= pd.to_datetime(date_from, errors="coerce")]
            d = pd.to_datetime(filtered["Issue_Date"], errors="coerce")
        if date_to:
            filtered = filtered[d <= pd.to_datetime(date_to, errors="coerce")]

    search = request.args.get("search")
    if search:
        mask = pd.Series(False, index=filtered.index)
        for col in filtered.columns:
            mask = mask | filtered[col].astype(str).str.contains(re.escape(search), case=False, na=False)
        filtered = filtered[mask]

    return jsonify({
        "has_data": True,
        "total": len(df),
        "count": len(filtered),
        "columns": list(df.columns),
        "records": _df_to_records(filtered),
    })


# Upload — same "never overwrite" filename logic as the original

@app.route("/api/upload", methods=["POST"])
def api_upload():
    BILL_IMAGE_DIR.mkdir(exist_ok=True)
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No file selected"}), 400

    ext = Path(f.filename).suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        return jsonify({"error": "Unsupported file type."}), 400

    stem = re.sub(r"[^\w\-. ]", "_", Path(f.filename).stem)
    candidate = BILL_IMAGE_DIR / f"{stem}{ext}"
    counter = 1
    while candidate.exists():
        candidate = BILL_IMAGE_DIR / f"{stem}_{counter}{ext}"
        counter += 1

    f.save(str(candidate))
    return jsonify({"filename": candidate.name})


# Processing pipeline — same five calls the original "Process Bill"
# button made, run in a background thread so the frontend can show
# real (not simulated) step-by-step progress by polling status.

JOBS = {}
JOBS_LOCK = threading.Lock()
PIPELINE_STEPS = ["convert", "clean", "ocr", "extract", "save"]


def _set_step(job_id, step, status):
    with JOBS_LOCK:
        JOBS[job_id]["steps"][step] = status


def _fail(job_id, message):
    with JOBS_LOCK:
        JOBS[job_id]["status"] = "error"
        JOBS[job_id]["message"] = message


def _run_pipeline(job_id, filename):
    candidate = BILL_IMAGE_DIR / filename
    ext = candidate.suffix.lower()

    _set_step(job_id, "convert", "running")
    image_paths = []
    if ext == ".pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(candidate)
            for i, pg in enumerate(doc):
                pix = pg.get_pixmap()
                out_path = BILL_IMAGE_DIR / f"{candidate.stem}_p{i + 1}.png"
                pix.save(str(out_path))
                image_paths.append(out_path)
            doc.close()
        except ImportError:
            _set_step(job_id, "convert", "error")
            _fail(job_id, "PDF support requires the 'pymupdf' package. Install it with: pip install pymupdf")
            return
        except Exception as e:
            _set_step(job_id, "convert", "error")
            _fail(job_id, f"Could not convert PDF to images: {e}")
            return
    else:
        image_paths = [candidate]
    _set_step(job_id, "convert", "done")

    try:
        _set_step(job_id, "clean", "running")
        from image_cleaning import image_cleaning
        image_cleaning(str(BILL_IMAGE_DIR), str(CLEANED_IMAGE_DIR))
        _set_step(job_id, "clean", "done")

        _set_step(job_id, "ocr", "running")
        from ocr_processor import perform_ocr
        perform_ocr(str(CLEANED_IMAGE_DIR), str(EXTRACTED_TEXT_FILE))
        _set_step(job_id, "ocr", "done")

        _set_step(job_id, "extract", "running")
        from parser import parse_multiple_invoices
        results = parse_multiple_invoices()
        if not results:
            _set_step(job_id, "extract", "error")
            _fail(job_id, "OCR ran, but no structured data could be extracted from the bill.")
            return
        _set_step(job_id, "extract", "done")

        _set_step(job_id, "save", "running")
        from data_insertion import insert_extracted_data
        insert_extracted_data()
        _set_step(job_id, "save", "done")

        with JOBS_LOCK:
            JOBS[job_id]["status"] = "success"

    except RuntimeError as e:
        current = next((s for s in PIPELINE_STEPS if JOBS[job_id]["steps"].get(s) == "running"), None)
        if current:
            _set_step(job_id, current, "error")
        _fail(job_id, f"AI service is unavailable: {e}. Please make sure Ollama is running.")
    except FileNotFoundError as e:
        current = next((s for s in PIPELINE_STEPS if JOBS[job_id]["steps"].get(s) == "running"), None)
        if current:
            _set_step(job_id, current, "error")
        _fail(job_id, f"Setup issue: {e}")
    except Exception as e:
        current = next((s for s in PIPELINE_STEPS if JOBS[job_id]["steps"].get(s) == "running"), None)
        if current:
            _set_step(job_id, current, "error")
        _fail(job_id, f"Something went wrong while processing the bill: {e}")


@app.route("/api/process", methods=["POST"])
def api_process():
    data = request.get_json(force=True, silent=True) or {}
    filename = data.get("filename")
    if not filename:
        return jsonify({"error": "filename is required"}), 400

    candidate = BILL_IMAGE_DIR / filename
    if not candidate.exists():
        return jsonify({"error": "File not found. Upload it first."}), 404

    job_id = uuid.uuid4().hex
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": "running",
            "message": None,
            "steps": {s: "pending" for s in PIPELINE_STEPS},
        }
    threading.Thread(target=_run_pipeline, args=(job_id, filename), daemon=True).start()
    return jsonify({"job_id": job_id})


@app.route("/api/process/status/<job_id>")
def api_process_status(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"error": "Unknown job id"}), 404
    return jsonify(job)


# AI Assistant — same natural-language -> SQL -> SQLite flow

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json(force=True, silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400

    try:
        sql_query_generation = response_to_user_query(question)
    except RuntimeError as e:
        return jsonify({"error": f"AI service is unavailable: {e}. Please make sure Ollama is running."}), 503
    except Exception:
        return jsonify({"error": "I couldn't process that question. Please try asking it differently."}), 500

    if not is_read_only_sql(sql_query_generation):
        return jsonify({
            "error": "I can only run read-only queries, and couldn't produce a safe one for that question. Try rephrasing it."
        }), 400

    output, err = run_query(sql_query_generation)
    if err:
        return jsonify({"error": f"I couldn't run that query: {err}"}), 500
    if output.empty:
        return jsonify({"sql": sql_query_generation, "columns": [], "rows": [], "empty": True})

    return jsonify({
        "sql": sql_query_generation,
        "columns": list(output.columns),
        "rows": _df_to_records(output),
        "empty": False,
    })


if __name__ == "__main__":
    app.run(debug=True, port=5000)
