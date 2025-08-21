# load_data.py
import sqlite3, json, re, math
from pathlib import Path

DB_PATH = "recipes.db"
JSON_PATH = "US_recipes.json"  # adjust if file is elsewhere

# Regex for calories like "389 kcal"
calorie_re = re.compile(r"(\d+(?:\.\d+)?)\s*kcal", re.I)

def to_int_or_none(x):
    try:
        if x is None: return None
        if isinstance(x, int): return x
        if isinstance(x, float): return None if math.isnan(x) else int(x)
        s = str(x).strip()
        return None if s.lower()=="nan" or s=="" else int(float(s))
    except: return None

def to_float_or_none(x):
    try:
        if x is None: return None
        if isinstance(x, (int,float)):
            return None if (isinstance(x,float) and math.isnan(x)) else float(x)
        s = str(x).strip()
        return None if s.lower()=="nan" or s=="" else float(s)
    except: return None

# --- Create DB ---
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
cur.executescript("""
DROP TABLE IF EXISTS recipes;
CREATE TABLE recipes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  cuisine TEXT,
  title TEXT,
  rating REAL,
  prep_time INTEGER,
  cook_time INTEGER,
  total_time INTEGER,
  description TEXT,
  nutrients TEXT,      -- store as JSON string
  serves TEXT,
  calories_int INTEGER -- numeric calories extracted from nutrients.calories
);
""")

# --- Load JSON ---
raw = json.loads(Path(JSON_PATH).read_text(encoding="utf-8"))
items = list(raw.values()) if isinstance(raw, dict) else raw

inserted = 0
for it in items:
    if not isinstance(it, dict): continue
    cuisine    = it.get("cuisine")
    title      = it.get("title")
    rating     = to_float_or_none(it.get("rating"))
    prep_time  = to_int_or_none(it.get("prep_time"))
    cook_time  = to_int_or_none(it.get("cook_time"))
    total_time = to_int_or_none(it.get("total_time"))
    description= it.get("description")
    nutrients  = it.get("nutrients") or {}
    if not isinstance(nutrients, dict): nutrients = {}
    serves     = it.get("serves")

    # extract numeric calories if present
    calories_int = None
    cal = nutrients.get("calories")
    if isinstance(cal, str):
        m = calorie_re.search(cal)
        if m:
            try: calories_int = int(float(m.group(1)))
            except: pass

    cur.execute("""
      INSERT INTO recipes
      (cuisine,title,rating,prep_time,cook_time,total_time,description,nutrients,serves,calories_int)
      VALUES (?,?,?,?,?,?,?,?,?,?)
    """, (cuisine,title,rating,prep_time,cook_time,total_time,description,
          json.dumps(nutrients, ensure_ascii=False), serves, calories_int))
    inserted += 1

conn.commit(); conn.close()
print(f"Inserted {inserted} recipes into {DB_PATH}")
