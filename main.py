# api/main.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3, json, re
from typing import Optional

DB_PATH = "../recipes.db"  # adjust path if needed

app = FastAPI(title="Recipes API", version="1.0.0")

# Allow requests from your React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Helpers ---
def dict_factory(cursor, row):
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    return conn

# regex for filters like <=400, >=4.5
_re = re.compile(r"^(<=|>=|=|<|>)?\s*([0-9]+(?:\.[0-9]+)?)$")

def parse_op_value(expr: str):
    expr = expr.strip()
    m = _re.match(expr)
    if not m:
        raise HTTPException(status_code=400, detail=f"Invalid filter: {expr}")
    return m.group(1) or "=", float(m.group(2))

ORDER = "ORDER BY (rating IS NULL) ASC, rating DESC"  # rating desc, NULLs last

# --- Endpoints ---
@app.get("/api/recipes")
def get_recipes(page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)):
    conn = get_conn(); cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as cnt FROM recipes")
    total = cur.fetchone()["cnt"]

    offset = (page - 1) * limit
    cur.execute(f"""
        SELECT id, title, cuisine, rating, prep_time, cook_time, total_time, description, nutrients, serves
        FROM recipes
        {ORDER}
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cur.fetchall()

    # parse nutrients JSON
    for r in rows:
        try:
            r["nutrients"] = json.loads(r["nutrients"]) if r.get("nutrients") else None
        except:
            r["nutrients"] = None

    return {"page": page, "limit": limit, "total": total, "data": rows}

@app.get("/api/recipes/search")
def search_recipes(
    title: Optional[str] = None,
    cuisine: Optional[str] = None,
    total_time: Optional[str] = Query(None, description="e.g., <=30"),
    rating: Optional[str] = Query(None, description="e.g., >=4.5"),
    calories: Optional[str] = Query(None, description="e.g., <=400"),
    page: int = Query(1, ge=1), limit: int = Query(10, ge=1, le=100)
):
    where, args = [], []
    if title:
        where.append("LOWER(title) LIKE ?"); args.append(f"%{title.lower()}%")
    if cuisine:
        where.append("LOWER(cuisine) = ?"); args.append(cuisine.lower())
    if total_time:
        op, val = parse_op_value(total_time); where.append(f"total_time {op} ?"); args.append(int(val))
    if rating:
        op, val = parse_op_value(rating); where.append(f"rating {op} ?"); args.append(float(val))
    if calories:
        op, val = parse_op_value(calories); where.append(f"calories_int {op} ?"); args.append(int(val))
    clause = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_conn(); cur = conn.cursor()
    cur.execute(f"SELECT COUNT(*) as cnt FROM recipes {clause}", args)
    total = cur.fetchone()["cnt"]

    offset = (page - 1) * limit
    cur.execute(f"""
        SELECT id, title, cuisine, rating, prep_time, cook_time, total_time, description, nutrients, serves
        FROM recipes
        {clause}
        {ORDER}
        LIMIT ? OFFSET ?
    """, args + [limit, offset])
    rows = cur.fetchall()

    for r in rows:
        try:
            r["nutrients"] = json.loads(r["nutrients"]) if r.get("nutrients") else None
        except:
            r["nutrients"] = None

    return {"page": page, "limit": limit, "total": total, "data": rows}
