"""
Synthetic D2C Haircare Brand - COD Orders Dataset Generator
Generates ~2000 rows with realistic RTO patterns for Indian market.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random

# ── Reproducibility ──────────────────────────────────────────────────────────
np.random.seed(42)
random.seed(42)

N = 2000
TODAY = datetime(2026, 10, 30)

# ── Pincode -> City -> State mapping (50 distinct pincodes) ────────────────────
PINCODE_DATA = [
    # Delhi NCR
    ("110001", "New Delhi",       "Delhi"),
    ("110002", "New Delhi",       "Delhi"),
    ("110003", "New Delhi",       "Delhi"),
    ("110011", "New Delhi",       "Delhi"),
    ("110019", "New Delhi",       "Delhi"),
    ("110044", "New Delhi",       "Delhi"),
    ("110085", "New Delhi",       "Delhi"),
    ("122001", "Gurugram",        "Haryana"),
    ("122002", "Gurugram",        "Haryana"),
    ("201301", "Noida",           "Uttar Pradesh"),
    ("201010", "Ghaziabad",       "Uttar Pradesh"),
    # Mumbai / Pune
    ("400001", "Mumbai",          "Maharashtra"),
    ("400051", "Mumbai",          "Maharashtra"),
    ("400068", "Mumbai",          "Maharashtra"),
    ("400703", "Navi Mumbai",     "Maharashtra"),
    ("411001", "Pune",            "Maharashtra"),
    ("411045", "Pune",            "Maharashtra"),
    # Bangalore / Chennai
    ("560001", "Bangalore",       "Karnataka"),
    ("560034", "Bangalore",       "Karnataka"),
    ("560068", "Bangalore",       "Karnataka"),
    ("560095", "Bangalore",       "Karnataka"),
    ("600001", "Chennai",         "Tamil Nadu"),
    ("600028", "Chennai",         "Tamil Nadu"),
    ("600096", "Chennai",         "Tamil Nadu"),
    # Hyderabad
    ("500001", "Hyderabad",       "Telangana"),
    ("500032", "Hyderabad",       "Telangana"),
    ("500081", "Hyderabad",       "Telangana"),
    # Kolkata
    ("700001", "Kolkata",         "West Bengal"),
    ("700091", "Kolkata",         "West Bengal"),
    ("700107", "Kolkata",         "West Bengal"),
    # Jaipur / Lucknow / Bhopal
    ("302001", "Jaipur",          "Rajasthan"),
    ("302017", "Jaipur",          "Rajasthan"),
    ("226001", "Lucknow",         "Uttar Pradesh"),
    ("226010", "Lucknow",         "Uttar Pradesh"),
    ("226022", "Lucknow",         "Uttar Pradesh"),
    ("462001", "Bhopal",          "Madhya Pradesh"),
    ("462016", "Bhopal",          "Madhya Pradesh"),
    # Ahmedabad / Surat
    ("380001", "Ahmedabad",       "Gujarat"),
    ("380015", "Ahmedabad",       "Gujarat"),
    ("395001", "Surat",           "Gujarat"),
    # Chandigarh / Amritsar
    ("160001", "Chandigarh",      "Chandigarh"),
    ("160017", "Chandigarh",      "Chandigarh"),
    ("143001", "Amritsar",        "Punjab"),
    # Patna / Ranchi / Bhubaneswar
    ("800001", "Patna",           "Bihar"),
    ("834001", "Ranchi",          "Jharkhand"),
    ("751001", "Bhubaneswar",     "Odisha"),
    # Indore / Nagpur / Coimbatore
    ("452001", "Indore",          "Madhya Pradesh"),
    ("440001", "Nagpur",          "Maharashtra"),
    ("641001", "Coimbatore",      "Tamil Nadu"),
]

# 8 "bad" pincodes with 55%+ RTO
BAD_PINCODES = {"800001", "834001", "110044", "201010", "462016", "143001", "700107", "226022"}

PINCODE_LIST  = [p[0] for p in PINCODE_DATA]
PINCODE_CITY  = {p[0]: p[1] for p in PINCODE_DATA}
PINCODE_STATE = {p[0]: p[2] for p in PINCODE_DATA}

# Pincode weights — bad pincodes get 3× traffic (more data, bad areas)
pincode_weights = np.array([3.0 if p[0] in BAD_PINCODES else 1.0 for p in PINCODE_DATA])
pincode_weights /= pincode_weights.sum()

# ── Name pools ───────────────────────────────────────────────────────────────
REAL_FIRST = [
    "Aarav","Aditya","Akash","Amit","Ananya","Anjali","Arjun","Aryan","Deepa",
    "Deepak","Divya","Gaurav","Geeta","Harpreet","Ishaan","Karan","Kavya",
    "Kritika","Manish","Meera","Mohit","Neeraj","Neha","Nikhil","Poonam",
    "Pooja","Priya","Rahul","Rajesh","Rakesh","Ravi","Rohit","Sachin","Sanjay",
    "Sapna","Shikha","Shreya","Siddharth","Simran","Sneha","Suresh","Swati",
    "Tanvi","Tanya","Uday","Varun","Vikram","Vishal","Yash","Zara",
]
REAL_LAST = [
    "Sharma","Verma","Singh","Kumar","Gupta","Patel","Shah","Mehta","Joshi",
    "Mishra","Yadav","Tiwari","Pandey","Chauhan","Agarwal","Bose","Das","Nair",
    "Iyer","Reddy","Rao","Pillai","Chatterjee","Banerjee","Mukherjee","Kapoor",
    "Malhotra","Bhatia","Sethi","Grover","Arora","Walia","Dhaliwal","Gill",
    "Siddiqui","Khan","Ansari","Shaikh","Qureshi","Mirza",
]
FAKE_NAMES = [
    "Test User","Asdf Kumar","aaa bbb","xyz","qwerty singh","zxcvbnm",
    "abcd efgh","aaaa bbbb","test test","dummy user","na na",
    "John Doe","fff ggg","hjkl pqrs",
]

def generate_name(is_fake: bool) -> str:
    if is_fake:
        return random.choice(FAKE_NAMES)
    return f"{random.choice(REAL_FIRST)} {random.choice(REAL_LAST)}"

# ── Phone numbers (allow repeat customers to share phone) ─────────────────────
# Pre-generate a pool of phones; some customers will reuse
PHONE_POOL_SIZE = 1400
phone_pool = [f"{random.choice([6,7,8,9])}{random.randint(100000000,999999999):09d}"
              for _ in range(PHONE_POOL_SIZE)]

# ── Address generators ────────────────────────────────────────────────────────
STREETS    = ["MG Road","Gandhi Nagar","Nehru Street","Rajaji Street","Station Road",
               "Civil Lines","Shastri Nagar","Model Town","Sector 14","DLF Phase 2"]
AREAS      = ["Koramangala","Laxmi Nagar","Andheri West","Banjara Hills","Salt Lake",
               "Malviya Nagar","Vaishali Nagar","Gomti Nagar","Baner","Jayanagar"]
LANDMARKS  = ["near Metro Station","opposite Central Park","near SBI Bank",
               "beside McDonald's","near Government Hospital"]

def good_address(city):
    num   = random.randint(1, 999)
    st    = random.choice(STREETS)
    area  = random.choice(AREAS)
    lm    = random.choice(LANDMARKS)
    return f"{num}, {st}, {area}, {city}, {lm}"

INCOMPLETE = [
    "near temple","opp school","house no 5","behind market","next to park",
    "near bus stop","in front of tower","lane 4","house no 12","near pond",
    "old colony","main road","near hospital","corner house","opposite ground",
]

HINGLISH = [
    "gali no 3, saamne wali dukaan ke paas, Laxmi Nagar",
    "pehli gali mein, neele rang ka makaan",
    "mandir ke peeche, teen numbri gali",
    "bada wala makaan, market ke paas",
    "school ke samne, lal darwaza wala ghar",
    "naya mohalla, kirana dukaan ke upar",
    "opp wali side mein, cycle stand ke paas",
    "purani basti, do manzila ghar",
    "chauraha ke paas, safed diwaar",
    "market ke andar, dawa dukaan ke bagal mein",
]

GIBBERISH = ["asdf","xxx","na","address","n/a","aaa","111","test","abc","12345","xyz123","----"]

def generate_address(addr_type, city):
    if addr_type == "good":
        return good_address(city)
    elif addr_type == "incomplete":
        return random.choice(INCOMPLETE)
    elif addr_type == "hinglish":
        return random.choice(HINGLISH)
    else:  # gibberish
        return random.choice(GIBBERISH)

# ── Build per-customer pool for repeat orders ─────────────────────────────────
# We'll assign a "customer_id" behind the scenes; some orders share same customer
NUM_UNIQUE_CUSTOMERS = 1400
customer_phones       = [random.choice(phone_pool) for _ in range(NUM_UNIQUE_CUSTOMERS)]
customer_total_orders = np.random.choice(range(1, 9), size=NUM_UNIQUE_CUSTOMERS,
                                          p=[0.40, 0.20, 0.14, 0.10, 0.07, 0.04, 0.03, 0.02])
customer_prev_rto     = np.array([
    np.random.randint(0, max(1, t)) if t > 1 else 0
    for t in customer_total_orders
])
customer_is_first     = (customer_total_orders == 1)

# ── Generate rows ─────────────────────────────────────────────────────────────
rows = []
for i in range(N):
    order_id   = f"ORD-{10001 + i:05d}"
    order_date = (TODAY - timedelta(days=random.randint(0, 89))).strftime("%Y-%m-%d")

    # Pick a customer
    cust_idx          = random.randint(0, NUM_UNIQUE_CUSTOMERS - 1)
    phone             = customer_phones[cust_idx]
    total_orders      = int(customer_total_orders[cust_idx])
    is_first          = bool(customer_is_first[cust_idx])
    prev_rto          = int(customer_prev_rto[cust_idx])

    # Name
    is_fake_name = random.random() < 0.05
    name         = generate_name(is_fake_name)

    # Pincode / city / state
    pincode = np.random.choice(PINCODE_LIST, p=pincode_weights)
    city    = PINCODE_CITY[pincode]
    state   = PINCODE_STATE[pincode]

    # Address type
    r = random.random()
    if r < 0.03:
        addr_type = "gibberish"
    elif r < 0.18:   # 0.03 + 0.15
        addr_type = "incomplete"
    elif r < 0.28:   # + 0.10
        addr_type = "hinglish"
    else:
        addr_type = "good"
    address = generate_address(addr_type, city)

    # Order financials
    order_value      = int(np.clip(np.random.normal(649, 280), 199, 1999))
    num_items        = random.randint(1, 5)
    product_category = random.choice(["Hair Oil","Shampoo","Conditioner","Hair Mask","Serum"])
    cod_amount       = order_value

    # ── RTO probability (combine signals with weights) ────────────────────────
    rto_prob = 0.28  # base

    if is_fake_name:
        rto_prob = max(rto_prob, 0.80)
    if addr_type == "gibberish":
        rto_prob = max(rto_prob, 0.75)
    elif addr_type == "incomplete":
        rto_prob = max(rto_prob, 0.50)

    if prev_rto > 0:
        rto_prob = max(rto_prob, 0.55)

    if is_first:
        rto_prob = max(rto_prob, 0.35)

    if order_value > 1200:
        rto_prob = min(rto_prob, 0.20)   # high-value -> lower RTO

    if pincode in BAD_PINCODES:
        rto_prob = max(rto_prob, 0.55)

    # Good profile -> very low RTO (only if no bad signals)
    if (addr_type == "good" and not is_first and prev_rto == 0
            and not is_fake_name and pincode not in BAD_PINCODES
            and order_value <= 1200):
        rto_prob = min(rto_prob, 0.08)

    # Add small noise
    rto_prob = np.clip(rto_prob + np.random.normal(0, 0.04), 0.0, 1.0)

    was_delivered = int(random.random() > rto_prob)

    # RTO reason
    rto_reason = ""
    if was_delivered == 0:
        if addr_type in ("gibberish", "incomplete"):
            rto_reason = random.choice(["Wrong address", "Fake address"])
        elif is_fake_name:
            rto_reason = random.choice(["Fake address", "Not reachable"])
        else:
            rto_reason = random.choice(["Not reachable","Refused delivery",
                                         "Not available","Wrong address"])

    rows.append({
        "order_id":                    order_id,
        "order_date":                  order_date,
        "customer_name":               name,
        "phone":                       phone,
        "address":                     address,
        "pincode":                     pincode,
        "city":                        city,
        "state":                       state,
        "order_value":                 order_value,
        "num_items":                   num_items,
        "product_category":            product_category,
        "is_first_order":              is_first,
        "customer_total_orders":       total_orders,
        "customer_previous_rto_count": prev_rto,
        "cod_amount":                  cod_amount,
        "was_delivered":               was_delivered,
        "rto_reason":                  rto_reason,
        "_addr_type":                  addr_type,   # temp column
        "_is_fake_name":               is_fake_name,  # temp column
    })

df = pd.DataFrame(rows)

# ── Compute pincode_historical_rto_rate ───────────────────────────────────────
pincode_rto = (
    df.groupby("pincode")["was_delivered"]
    .apply(lambda x: round(1 - x.mean(), 4))
    .rename("pincode_historical_rto_rate")
)
df = df.merge(pincode_rto, on="pincode")

# Drop temp columns before saving
df.drop(columns=["_addr_type", "_is_fake_name"], inplace=True)

# ── Save CSV ──────────────────────────────────────────────────────────────────
OUT_PATH = r"C:\Users\vansh\.gemini\antigravity\scratch\cod-rto-engine\data\orders_sample.csv"
df.to_csv(OUT_PATH, index=False)
print(f"[OK] Saved {len(df)} rows -> {OUT_PATH}\n")

# ── Summary Statistics ────────────────────────────────────────────────────────
total         = len(df)
rto_overall   = round(1 - df["was_delivered"].mean(), 4)

first_mask    = df["is_first_order"] == True
repeat_mask   = df["is_first_order"] == False
rto_first     = round(1 - df[first_mask]["was_delivered"].mean(), 4)
rto_repeat    = round(1 - df[repeat_mask]["was_delivered"].mean(), 4)

top5_pincodes = (
    df.groupby(["pincode","city"])["was_delivered"]
    .apply(lambda x: round(1 - x.mean(), 4))
    .reset_index(name="rto_rate")
    .sort_values("rto_rate", ascending=False)
    .head(5)
)

# Re-create temp flag for stats only
fake_names_in_pool = set(n.lower() for n in FAKE_NAMES)
fake_count = df["customer_name"].apply(lambda n: n.lower() in fake_names_in_pool).sum()

print("=" * 55)
print("        SYNTHETIC DATASET SUMMARY STATISTICS")
print("=" * 55)
print(f"  Total orders          : {total:,}")
print(f"  Overall RTO rate      : {rto_overall*100:.2f}%")
print(f"  RTO – First-time      : {rto_first*100:.2f}%")
print(f"  RTO – Repeat customer : {rto_repeat*100:.2f}%")
print()
print("  Top 5 High-RTO Pincodes:")
for _, row in top5_pincodes.iterrows():
    print(f"    {row['pincode']} ({row['city']:<18}) -> {row['rto_rate']*100:.1f}%")
print()
print(f"  Fake names detected   : {fake_count}")
print("=" * 55)
print()

# Extra breakdown
print("  RTO by address type:")
temp = rows  # reuse list of dicts that still has _addr_type
temp_df = pd.DataFrame(temp)[["_addr_type","was_delivered"]]
for atype, grp in temp_df.groupby("_addr_type"):
    r = round(1 - grp["was_delivered"].mean(), 4)
    print(f"    {atype:<12} -> {r*100:.1f}%  (n={len(grp)})")

print()
print("  RTO by product category:")
for cat, grp in df.groupby("product_category"):
    r = round(1 - grp["was_delivered"].mean(), 4)
    print(f"    {cat:<15} -> {r*100:.1f}%  (n={len(grp)})")
