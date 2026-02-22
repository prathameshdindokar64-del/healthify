from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = 'heathify_premium_secret_key_2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///heathify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ==============================================================================
# MODELS
# ==============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    points = db.Column(db.Integer, default=0)
    last_login_bonus = db.Column(db.String(20), default='')  # date string
    profile = db.relationship('Profile', backref='user', uselist=False)
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

class Profile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    age = db.Column(db.Integer)
    height = db.Column(db.Float)   # cm
    weight = db.Column(db.Float)   # kg
    gender = db.Column(db.String(20), default='Other')
    goal = db.Column(db.String(50), default='Stay Healthy')
    activity_level = db.Column(db.String(50), default='Moderate')
    conditions = db.Column(db.String(500), default='[]')  # JSON list

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    price_inr = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    category = db.Column(db.String(100), default='')

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    items_json = db.Column(db.Text)
    subtotal = db.Column(db.Float)
    gst_amount = db.Column(db.Float)
    discount = db.Column(db.Float, default=0)
    grand_total = db.Column(db.Float)
    address = db.Column(db.String(500))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    points_used = db.Column(db.Integer, default=0)

# ==============================================================================
# PRODUCTS CATALOGUE (INR)
# ==============================================================================

PRODUCTS = [
    # ── Existing Classics ─────────────────────────────────────────────────────
    {"id": 1,  "name": "Royal Gala Apple",        "price": 999,   "unit": "ea",     "category": "Organic Fruits",      "img": "https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?auto=format&fit=crop&w=600&q=80", "desc": "Washed in Himalayan mineral water. Hand-picked at dawn."},
    {"id": 2,  "name": "Symphony Kale",            "price": 499,   "unit": "bunch",  "category": "Vegetables",          "img": "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=600&q=80", "desc": "Grown in the presence of classical music to reduce cellular stress."},
    {"id": 3,  "name": "24K Gold Leaf Salad",      "price": 750,   "unit": "box",    "category": "Salads",              "img": "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=600&q=80", "desc": "Microgreens dusted with edible gold. Because you can."},
    {"id": 4,  "name": "Monastic Silken Tofu",     "price": 1850,  "unit": "pack",   "category": "Vegan & Tofu",        "img": "https://images.unsplash.com/photo-1582408922808-f2e2e7e4a2f0?auto=format&fit=crop&w=600&q=80", "desc": "Hand-pressed by artisans. 0% GMO, 100% Zen."},
    {"id": 5,  "name": "Isolate No. 5",            "price": 8499,  "unit": "kg",     "category": "Protein",             "img": "https://images.unsplash.com/photo-1593095948071-474c5cc2989d?auto=format&fit=crop&w=600&q=80", "desc": "The purest protein structure known to man. Bio-available luxury."},
    {"id": 6,  "name": "Heritage A2 Milk",         "price": 1100,  "unit": "ltr",    "category": "Dairy",               "img": "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=600&q=80", "desc": "From cows that are happier than you. Raw, untouched."},
    {"id": 7,  "name": "The Noir Brownie",         "price": 1200,  "unit": "ea",     "category": "Sugarless",           "img": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=600&q=80", "desc": "Zero Sugar. Zero Guilt. Pure Cacao. Eat like you own the place."},
    {"id": 8,  "name": "Himalayan Ashwagandha",    "price": 1599,  "unit": "box",    "category": "Supplements",         "img": "https://images.unsplash.com/photo-1585435557343-3b092031a831?auto=format&fit=crop&w=600&q=80", "desc": "Ancient adaptogen, cold-extracted for maximum bioavailability."},
    {"id": 9,  "name": "Artisan Quinoa Reserve",   "price": 1199,  "unit": "kg",     "category": "Grains",              "img": "https://images.unsplash.com/photo-1543362906-acfc16c67564?auto=format&fit=crop&w=600&q=80", "desc": "Sourced from Andean highlands. Triple-rinsed, sun-dried perfection."},

    # ── 16. Energy Bars ───────────────────────────────────────────────────────
    {"id": 16, "name": "Apex Nut & Date Bar",      "price": 179,   "unit": "ea",     "category": "Energy Bars",         "img": "https://images.unsplash.com/photo-1607688387751-c1e95ae09a42?auto=format&fit=crop&w=600&q=80", "desc": "Dates, almonds & dark cacao. No refined sugar. 220 kcal of clean fuel."},
    {"id": 17, "name": "Warrior Protein Bar",       "price": 199,   "unit": "ea",     "category": "Energy Bars",         "img": "https://images.unsplash.com/photo-1571019614242-c5c5dee9f50b?auto=format&fit=crop&w=600&q=80", "desc": "20g whey protein, 5g fibre, zero artificial sweeteners. Pre-workout gold."},
    {"id": 18, "name": "Matcha Oat Energy Bar",    "price": 159,   "unit": "ea",     "category": "Energy Bars",         "img": "https://images.unsplash.com/photo-1556679343-c7306c1976bc?auto=format&fit=crop&w=600&q=80", "desc": "Ceremonial-grade matcha, rolled oats & honey. Sustained focus all day."},

    # ── 17. Seeds for Good Health ─────────────────────────────────────────────
    {"id": 19, "name": "Chia Seeds Reserve",        "price": 499,   "unit": "250g",   "category": "Seeds & Superfoods", "img": "https://images.unsplash.com/photo-1515879218367-8466d910aaa4?auto=format&fit=crop&w=600&q=80", "desc": "Omega-3 powerhouse. Cold-processed to preserve all fatty acids."},
    {"id": 20, "name": "Flax Seed Gold",            "price": 349,   "unit": "500g",   "category": "Seeds & Superfoods", "img": "https://images.unsplash.com/photo-1588167056547-c183313da96e?auto=format&fit=crop&w=600&q=80", "desc": "Lignans, fibre & Omega-3. Freshly cold-milled for peak bioavailability."},
    {"id": 21, "name": "Pumpkin & Sunflower Mix",  "price": 599,   "unit": "300g",   "category": "Seeds & Superfoods", "img": "https://images.unsplash.com/photo-1600803907087-f56d462fd26b?auto=format&fit=crop&w=600&q=80", "desc": "Premium roasted seed blend — zinc, magnesium & Vitamin E in every handful."},

    # ── 18. Dry Fruits (Indian grown & imported) ──────────────────────────────
    {"id": 22, "name": "Kashmir Premium Walnuts",  "price": 1299,  "unit": "250g",   "category": "Dry Fruits",          "img": "https://images.unsplash.com/photo-1563412885-139e09b4ef68?auto=format&fit=crop&w=600&q=80", "desc": "Grade A Kashmiri walnuts. Brain-boosting Omega-3 with papery thin shells."},
    {"id": 23, "name": "Afghani Seedless Raisins", "price": 449,   "unit": "500g",   "category": "Dry Fruits",          "img": "https://images.unsplash.com/photo-1499638673689-79a0b5115d87?auto=format&fit=crop&w=600&q=80", "desc": "Sun-dried Afghani green raisins. Iron-rich & naturally sweet."},
    {"id": 24, "name": "Roasted Almonds Royale",   "price": 899,   "unit": "250g",   "category": "Dry Fruits",          "img": "https://images.unsplash.com/photo-1508061253366-f7da158b6d46?auto=format&fit=crop&w=600&q=80", "desc": "California & Indian almonds, slow-roasted with Himalayan sea salt."},

    # ── 19. Non-Veg Proteins ──────────────────────────────────────────────────
    {"id": 25, "name": "Farm-Fresh Desi Eggs",     "price": 199,   "unit": "12 pcs", "category": "Non-Veg Protein",    "img": "https://images.unsplash.com/photo-1506976785307-8732e854ad03?auto=format&fit=crop&w=600&q=80", "desc": "Free-range country eggs. Richer yolk, higher Omega-3. No cage, no compromise."},
    {"id": 26, "name": "Himalayan Stream Trout",   "price": 899,   "unit": "500g",   "category": "Non-Veg Protein",    "img": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=600&q=80", "desc": "Cold-water trout. Omega-3 dense, sustainably caught, flash-frozen at source."},
    {"id": 27, "name": "Organic Desi Chicken",     "price": 699,   "unit": "500g",   "category": "Non-Veg Protein",    "img": "https://images.unsplash.com/photo-1604503468506-a8da13d82791?auto=format&fit=crop&w=600&q=80", "desc": "Open-farm desi breed. No hormones, no antibiotics. 29g protein per 100g."},

    # ── 20. Cold Pressed Oils, Ghee ───────────────────────────────────────────
    {"id": 28, "name": "A2 Bilona Ghee",            "price": 1999,  "unit": "500ml",  "category": "Oils & Ghee",        "img": "https://images.unsplash.com/photo-1628689469838-524a4a973b8e?auto=format&fit=crop&w=600&q=80", "desc": "Hand-churned from cultured A2 milk. Ancient Vedic bilona method — pure gold."},
    {"id": 29, "name": "Wood-Pressed Coconut Oil", "price": 799,   "unit": "500ml",  "category": "Oils & Ghee",        "img": "https://images.unsplash.com/photo-1598373182133-52452f7691ef?auto=format&fit=crop&w=600&q=80", "desc": "Cold-pressed virgin coconut oil. High lauric acid, smoke point 177°C."},
    {"id": 30, "name": "Black Seed Kalonji Oil",   "price": 699,   "unit": "250ml",  "category": "Oils & Ghee",        "img": "https://images.unsplash.com/photo-1620706857370-e1b9770e8bb1?auto=format&fit=crop&w=600&q=80", "desc": "Nigella sativa cold-pressed oil. Anti-inflammatory, immunity booster."},

    # ── 21. Organic Flours, Millets, Rice ────────────────────────────────────
    {"id": 31, "name": "Foxtail Millet Flour",     "price": 299,   "unit": "1kg",    "category": "Flours & Millets",   "img": "https://images.unsplash.com/photo-1574323347407-f5e1ad6d020b?auto=format&fit=crop&w=600&q=80", "desc": "Ancient Indian millet. Low GI (50), gluten-free. Swap your wheat today."},
    {"id": 32, "name": "Organic Basmati Reserve",  "price": 499,   "unit": "1kg",    "category": "Flours & Millets",   "img": "https://images.unsplash.com/photo-1516684732162-798a0062be99?auto=format&fit=crop&w=600&q=80", "desc": "Aged Dehradun basmati — long-grain, aromatic, hand-sorted perfection."},
    {"id": 33, "name": "Ragi & Jowar Mix Flour",   "price": 349,   "unit": "1kg",    "category": "Flours & Millets",   "img": "https://images.unsplash.com/photo-1565087906467-e12ef95e4db5?auto=format&fit=crop&w=600&q=80", "desc": "Ancient millet blend. Calcium-dense, fibre-rich, diabetic-friendly."},

    # ── 23. Teas, Coffee & Beverages ──────────────────────────────────────────
    {"id": 34, "name": "First Flush Darjeeling Tea","price": 899,  "unit": "100g",   "category": "Teas & Beverages",   "img": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?auto=format&fit=crop&w=600&q=80", "desc": "Second-flush FTGFOP1 grade. The champagne of teas — muscatel, floral, divine."},
    {"id": 35, "name": "Ceremonial Matcha Grade A", "price": 1299, "unit": "50g",    "category": "Teas & Beverages",   "img": "https://images.unsplash.com/photo-1536256263959-770b48d82b0a?auto=format&fit=crop&w=600&q=80", "desc": "Shade-grown Japanese matcha. L-Theanine + caffeine — alert calm in a cup."},
    {"id": 36, "name": "Cold Brew Coffee Blend",    "price": 749,  "unit": "200g",   "category": "Teas & Beverages",   "img": "https://images.unsplash.com/photo-1461023058943-07fcbe16d735?auto=format&fit=crop&w=600&q=80", "desc": "Single-origin Coorg arabica, coarsely ground for 18-hour cold steep."},

    # ── 24. Spices & Seasonings ───────────────────────────────────────────────
    {"id": 37, "name": "Kashmir Saffron (Kesar)",   "price": 1499, "unit": "1g",     "category": "Spices & Seasonings","img": "https://images.unsplash.com/photo-1612804890655-b9c5d3b35bb6?auto=format&fit=crop&w=600&q=80", "desc": "Grade A Kashmiri saffron. 31,000+ threads per kg. Mood, sleep & skin booster."},
    {"id": 38, "name": "Organic Turmeric Reserve",  "price": 299,  "unit": "200g",   "category": "Spices & Seasonings","img": "https://images.unsplash.com/photo-1587049352851-8d4e89133924?auto=format&fit=crop&w=600&q=80", "desc": "5%+ curcumin content. Cold-dried Alleppey turmeric — the real anti-inflammatory."},
    {"id": 39, "name": "Black Pepper Tellicherry",  "price": 399,  "unit": "250g",   "category": "Spices & Seasonings","img": "https://images.unsplash.com/photo-1599318980903-853f897b4edd?auto=format&fit=crop&w=600&q=80", "desc": "Extra-bold Malabar peppercorns. Piperine-rich — unlocks curcumin absorption."},

    # ── 25. Snacks ────────────────────────────────────────────────────────────
    {"id": 40, "name": "Roasted Makhana (Fox Nuts)","price": 399,  "unit": "200g",   "category": "Snacks",             "img": "https://images.unsplash.com/photo-1604517263946-b21dc79f0a25?auto=format&fit=crop&w=600&q=80", "desc": "Himalayan lotus seeds, slow-roasted. Low calorie, high protein. Zero guilt."},
    {"id": 41, "name": "Baked Ragi Crackers",       "price": 249,  "unit": "150g",   "category": "Snacks",             "img": "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=600&q=80", "desc": "Gluten-free ragi & sesame crackers. Calcium powerhouse in every bite."},
    {"id": 42, "name": "Mixed Seed Trail Mix",      "price": 549,  "unit": "300g",   "category": "Snacks",             "img": "https://images.unsplash.com/photo-1596591606975-97ee5cef3a1e?auto=format&fit=crop&w=600&q=80", "desc": "Pumpkin, flax, sunflower & cranberry. The premium hiker's power pack."},

    # ── 26. Ketchup & Condiments ──────────────────────────────────────────────
    {"id": 43, "name": "No-Sugar Tomato Ketchup",  "price": 299,  "unit": "500g",   "category": "Condiments",         "img": "https://images.unsplash.com/photo-1590005354167-6da97870c757?auto=format&fit=crop&w=600&q=80", "desc": "Made with farm-grown tomatoes. Stevia-sweetened — same taste, zero guilt."},
    {"id": 44, "name": "Wild Kasundi Mustard",      "price": 349,  "unit": "200g",   "category": "Condiments",         "img": "https://images.unsplash.com/photo-1553361371-9b22f78e8b1d?auto=format&fit=crop&w=600&q=80", "desc": "Bengali whole-grain mustard. Raw-fermented, probiotic-rich, deeply aromatic."},
    {"id": 45, "name": "Organic Apple Cider Vinegar","price": 499, "unit": "500ml",  "category": "Condiments",         "img": "https://images.unsplash.com/photo-1587854692152-cbe660dbde88?auto=format&fit=crop&w=600&q=80", "desc": "Raw, unfiltered with the mother. Gut health, blood sugar & weight management."},

    # ── 27. Natural Sweeteners ────────────────────────────────────────────────
    {"id": 46, "name": "Raw Multiflora Honey",      "price": 699,  "unit": "500g",   "category": "Natural Sweeteners", "img": "https://images.unsplash.com/photo-1558642452-9d2a7deb7f62?auto=format&fit=crop&w=600&q=80", "desc": "Wild-harvested from the Sundarbans. Unheated, enzyme-rich, antifungal."},
    {"id": 47, "name": "Coconut Sugar Crystal",     "price": 399,  "unit": "500g",   "category": "Natural Sweeteners", "img": "https://images.unsplash.com/photo-1510009819083-c94e6b9f2c88?auto=format&fit=crop&w=600&q=80", "desc": "Low GI (35) palm sugar. Caramel flavour, mineral-rich. 1:1 sugar swap."},
    {"id": 48, "name": "Stevia Gold Drops",         "price": 499,  "unit": "30ml",   "category": "Natural Sweeteners", "img": "https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&w=600&q=80", "desc": "Zero-calorie plant-based sweetener. 300× sweeter than sugar. Diabetic safe."},
]

# ==============================================================================
# GAMIFICATION HELPERS
# ==============================================================================

def award_points(user_id, amount, label=""):
    user = User.query.get(user_id)
    if user:
        user.points += amount
        db.session.commit()
        session['points_toast'] = f"+{amount} pts — {label}" if label else f"+{amount} pts"
        session['user_points'] = user.points

def get_user_tier(points):
    if points >= 10000: return "Obsidian"
    if points >= 5000:  return "Platinum"
    if points >= 2000:  return "Gold"
    if points >= 500:   return "Silver"
    return "Bronze"

# ==============================================================================
# AI DAY PLAN GENERATOR
# ==============================================================================

def generate_day_plan(profile, user_name):
    """Rule-based AI day plan tailored to user profile + Heathify products."""
    conditions = json.loads(profile.conditions) if profile and profile.conditions else []
    age = profile.age if profile else 25
    weight = profile.weight if profile else 65
    goal = profile.goal if profile else "Stay Healthy"
    activity = profile.activity_level if profile else "Moderate"

    # BMI calculation
    height_m = (profile.height / 100) if profile and profile.height else 1.70
    bmi = round(weight / (height_m ** 2), 1) if weight else 22

    # Calorie target
    base_cal = 2000
    if activity == "High":       base_cal = 2400
    elif activity == "Low":      base_cal = 1700
    if goal == "Lose Weight":    base_cal -= 300
    elif goal == "Build Muscle": base_cal += 200

    # Condition-specific tweaks
    is_diabetic  = any(c in conditions for c in ["Diabetes T1", "Diabetes T2"])
    has_pcos     = "PCOS" in conditions
    has_ibs      = "IBS" in conditions or "Crohns" in conditions
    is_vegan     = "Vegan" in conditions

    # Morning
    if is_diabetic or has_pcos:
        morning = "Methi Water + Chia Seed Pudding (no sugar)"
        morning_product = "Artisan Quinoa Reserve — low-GI starter"
    elif has_ibs:
        morning = "Warm ginger tea + plain Rice Porridge"
        morning_product = "Heritage A2 Milk — gentle on gut"
    else:
        morning = "Matcha Latte + Overnight Oats"
        morning_product = "Heritage A2 Milk — farm-fresh protein boost"

    # Lunch
    if is_vegan or "Vegan" in str(goal):
        lunch = "Quinoa Buddha Bowl with roasted chickpeas & tahini"
        lunch_product = "Artisan Quinoa Reserve + Monastic Silken Tofu"
    elif is_diabetic:
        lunch = "Grilled tofu wrap with leafy greens (no white bread)"
        lunch_product = "Monastic Silken Tofu + Symphony Kale"
    else:
        lunch = "Kale & Quinoa Power Bowl with olive oil dressing"
        lunch_product = "Symphony Kale + Artisan Quinoa Reserve"

    # Dinner
    if goal == "Build Muscle":
        dinner = "Grilled chicken breast + steamed broccoli + brown rice"
        dinner_product = "Isolate No. 5 — post-dinner protein shake"
    elif goal == "Lose Weight":
        dinner = "Soup of the day: mixed vegetables + lentil broth"
        dinner_product = "Symphony Kale — detox evening soup base"
    else:
        dinner = "Baked salmon / tofu steak + roasted root vegetables"
        dinner_product = "Monastic Silken Tofu — artisan evening protein"

    # Snacks
    snack = "Royal Gala Apple + Himalayan Ashwagandha capsule (stress adaption)" if age >= 30 else "Royal Gala Apple + handful of mixed nuts"
    snack_product = "Royal Gala Apple + Himalayan Ashwagandha"

    # Water & supplements
    water_goal = max(2.5, round(weight * 0.033, 1))

    plan = {
        "user_name": user_name,
        "bmi": bmi,
        "calorie_target": base_cal,
        "water_goal": water_goal,
        "goal": goal,
        "tier": get_user_tier(0),
        "schedule": [
            {"time": "06:30 AM", "meal": "Wake-up Ritual", "dish": morning, "product": morning_product},
            {"time": "10:00 AM", "meal": "Mid-Morning Snack", "dish": snack, "product": snack_product},
            {"time": "01:00 PM", "meal": "Lunch", "dish": lunch, "product": lunch_product},
            {"time": "04:00 PM", "meal": "Afternoon Boost", "dish": "24K Gold Leaf Salad or fruit", "product": "24K Gold Leaf Salad — micronutrient hit"},
            {"time": "07:30 PM", "meal": "Dinner", "dish": dinner, "product": dinner_product},
            {"time": "09:30 PM", "meal": "Night Wind-Down", "dish": "Golden turmeric milk / The Noir Brownie (guilt-free treat)", "product": "The Noir Brownie — zero sugar indulgence"},
        ],
        "tips": [
            f"Target {base_cal} kcal today based on your {activity.lower()} activity level.",
            f"Drink at least {water_goal}L of water. Your weight suggests this need.",
            "Avoid processed sugars — opt for Heathify's sugarless range.",
            "Log your meals in the Lifestyle section to earn points.",
        ]
    }
    return plan

# ==============================================================================
# CHATBOT ENGINE
# ==============================================================================

def chatbot_response(message, user_name="friend"):
    msg = message.lower()
    responses = {
        "weight":    f"Hi {user_name}! For healthy weight management, focus on a calorie deficit of 300-500 kcal/day. Try our Symphony Kale & Quinoa bowls — low calorie, high satiety! 🥗",
        "protein":   f"Great question! Aim for 0.8–1.2g of protein per kg of body weight. Our **Isolate No. 5** protein (₹12,499/kg) is the finest bio-available whey you'll find. 💪",
        "diet":      f"A balanced diet for you should include 40% carbs, 30% protein, 30% fats. Heathify's meal kits are curated precisely for your profile! Check your Dashboard day plan. 🌿",
        "sleep":     f"Sleep is the most underrated health tool! Aim for 7–9 hrs. Our **Himalayan Ashwagandha** supplement helps reduce cortisol for deeper sleep. 😴",
        "sugar":     f"Cutting sugar? Smart move! Try **The Noir Brownie** — zero sugar, pure cacao bliss. Also, our A2 Milk has natural low-GI sugars only. 🍫",
        "diabetes":  f"For diabetes management, prioritize low-GI foods: our Artisan Quinoa (GI 53) and Monastic Silken Tofu are excellent choices. Always consult your doctor! 🩺",
        "energy":    f"Feeling sluggish? Hydration is key — drink {2.5}L+ water daily. Our Matcha range and Ashwagandha supplements restore energy naturally. ⚡",
        "vitamin":   f"Vitamins come from whole foods! Our 24K Gold Leaf Salad is packed with Vitamins A, C, K & folate. One box = your daily micronutrient target. 🥬",
        "workout":   f"Pre-workout: Royal Gala Apple + Isolate No. 5 shake. Post-workout: Heritage A2 Milk + The Noir Brownie. Perfectly timed nutrition! 🏋️",
        "stress":    f"Stress is the silent killer of health goals. Our **Himalayan Ashwagandha** is clinically linked to a 27% cortisol reduction. Breathe deep, {user_name}. 🌸",
        "immune":    f"Immunity boosters: Vitamin C (Royal Gala Apple), Zinc (Tofu), Adaptogens (Ashwagandha). All in our store! 🛡️",
        "heart":     f"For heart health: eat more Omega-3s (flaxseeds, fatty fish), reduce sodium, and stay active. Our Kale & Quinoa bowl is cardio-protective! ❤️",
        "gut":       f"Happy gut = happy life! Try our A2 Milk (easier to digest than A1), Kale (prebiotic fibre), and avoid processed foods. Probiotic tip: add yogurt! 🦠",
        "points":    f"You earn points for daily logins, purchases, and activities! Redeem them as cash discounts on your next order. Visit your cart/checkout to redeem. ⭐",
        "hello":     f"Hey {user_name}! 👋 I'm your Heathify Health Coach. Ask me anything about diet, nutrition, sleep, stress, or our products!",
        "hi":        f"Hello {user_name}! ✨ Ready to optimise your health today? Ask me about nutrition, products, your day plan, or anything wellness-related!",
    }
    for keyword, reply in responses.items():
        if keyword in msg:
            return reply

    # Default
    return (
        f"Great question, {user_name}! 🌿 As your personal health coach, I'd suggest focusing on whole foods, "
        "adequate sleep, and consistent movement. For personalised advice on: **diet** 🥗 | **weight** 💪 | "
        "**sleep** 😴 | **stress** 🧘 | **energy** ⚡ — just ask me! I'm here 24/7."
    )

# ==============================================================================
# ROUTES — AUTH
# ==============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/auth/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id']   = user.id
            session['user_name'] = user.name
            session['user_points'] = user.points
            # Daily login bonus
            today_str = str(date.today())
            if user.last_login_bonus != today_str:
                user.last_login_bonus = today_str
                db.session.commit()
                award_points(user.id, 10, "Daily Login Bonus")
                flash('🌟 +10 points for today\'s login! Keep the streak!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid credentials. Access denied.', 'error')
    return render_template('auth/login.html')

@app.route('/auth/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        name     = request.form['name']
        if User.query.filter_by(username=username).first():
            flash('Username already exists.', 'error')
            return redirect(url_for('signup'))
        hashed_pw = generate_password_hash(password)
        new_user = User(username=username, password=hashed_pw, name=name, points=0)
        db.session.add(new_user)
        db.session.commit()
        session['user_id']     = new_user.id
        session['user_name']   = new_user.name
        session['user_points'] = 0
        return redirect(url_for('profile_setup'))
    return render_template('auth/signup.html')

@app.route('/auth/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ==============================================================================
# ROUTES — PROFILE
# ==============================================================================

@app.route('/profile/setup', methods=['GET', 'POST'])
def profile_setup():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        user_id = session['user_id']
        profile = Profile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = Profile(user_id=user_id)
            db.session.add(profile)
        profile.age            = request.form.get('age')
        profile.height         = request.form.get('height')
        profile.weight         = request.form.get('weight')
        profile.gender         = request.form.get('gender', 'Other')
        profile.goal           = request.form.get('goal', 'Stay Healthy')
        profile.activity_level = request.form.get('activity_level', 'Moderate')
        conditions_list        = request.form.getlist('conditions')
        profile.conditions     = json.dumps(conditions_list)
        db.session.commit()
        award_points(user_id, 100, "Profile Setup Complete")
        flash('🎉 +100 points! Your profile is now initialized.', 'success')
        return redirect(url_for('dashboard'))
    return render_template('profile/setup.html')

# ==============================================================================
# ROUTES — DASHBOARD
# ==============================================================================

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user    = User.query.get(session['user_id'])
    profile = Profile.query.filter_by(user_id=user.id).first()
    plan    = generate_day_plan(profile, user.name)
    plan['tier']   = get_user_tier(user.points)
    plan['points'] = user.points
    session['user_points'] = user.points
    toast = session.pop('points_toast', None)
    return render_template('dashboard.html', plan=plan, user=user, profile=profile, toast=toast)

# ==============================================================================
# ROUTES — SHOP & CART
# ==============================================================================

@app.route('/shop')
def shop():
    return render_template('shop.html', products=PRODUCTS)

@app.route('/cart')
def cart():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    subtotal = sum(i.price_inr * i.quantity for i in items)
    gst = round(subtotal * 0.18, 2)
    grand = round(subtotal + gst, 2)
    user = User.query.get(session['user_id'])
    return render_template('cart.html', items=items, subtotal=subtotal, gst=gst, grand=grand, user=user)

@app.route('/cart/add', methods=['POST'])
def cart_add():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Login required'}), 401
    data = request.get_json()
    product_name = data.get('name')
    price_inr    = float(data.get('price', 0))
    category     = data.get('category', '')
    user_id      = session['user_id']
    existing = CartItem.query.filter_by(user_id=user_id, product_name=product_name).first()
    if existing:
        existing.quantity += 1
    else:
        item = CartItem(user_id=user_id, product_name=product_name, price_inr=price_inr, category=category)
        db.session.add(item)
    db.session.commit()
    count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(user_id=user_id).scalar() or 0
    return jsonify({'success': True, 'cart_count': int(count), 'message': f'{product_name} added to cart!'})

@app.route('/cart/remove', methods=['POST'])
def cart_remove():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401
    data = request.get_json()
    item_id = data.get('item_id')
    item = CartItem.query.filter_by(id=item_id, user_id=session['user_id']).first()
    if item:
        db.session.delete(item)
        db.session.commit()
    return jsonify({'success': True})

@app.route('/cart/update', methods=['POST'])
def cart_update():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401
    data = request.get_json()
    item_id  = data.get('item_id')
    quantity = int(data.get('quantity', 1))
    item = CartItem.query.filter_by(id=item_id, user_id=session['user_id']).first()
    if item:
        if quantity <= 0:
            db.session.delete(item)
        else:
            item.quantity = quantity
        db.session.commit()
    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    subtotal = sum(i.price_inr * i.quantity for i in items)
    gst = round(subtotal * 0.18, 2)
    grand = round(subtotal + gst, 2)
    count = sum(i.quantity for i in items)
    return jsonify({'success': True, 'subtotal': subtotal, 'gst': gst, 'grand': grand, 'count': count})

# ==============================================================================
# ROUTES — CHECKOUT
# ==============================================================================

@app.route('/checkout')
def checkout():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    items = CartItem.query.filter_by(user_id=session['user_id']).all()
    if not items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
    user     = User.query.get(session['user_id'])
    subtotal = sum(i.price_inr * i.quantity for i in items)
    gst      = round(subtotal * 0.18, 2)
    grand    = round(subtotal + gst, 2)
    return render_template('checkout.html', items=items, subtotal=subtotal, gst=gst, grand=grand, user=user)

@app.route('/checkout/place', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    user    = User.query.get(user_id)
    items   = CartItem.query.filter_by(user_id=user_id).all()
    if not items:
        return redirect(url_for('cart'))

    address       = request.form.get('address', '')
    points_to_use = int(request.form.get('points_redeem', 0))
    # Cap: can't redeem more than they have, max 20% discount
    points_to_use = min(points_to_use, user.points)
    subtotal      = sum(i.price_inr * i.quantity for i in items)
    gst           = round(subtotal * 0.18, 2)
    discount      = min(points_to_use, round((subtotal + gst) * 0.20))  # ₹1 per point, max 20% off
    grand         = round(subtotal + gst - discount, 2)

    items_json = json.dumps([{"name": i.product_name, "qty": i.quantity, "price": i.price_inr} for i in items])
    order = Order(
        user_id=user_id, items_json=items_json,
        subtotal=subtotal, gst_amount=gst,
        discount=discount, grand_total=grand,
        address=address, points_used=points_to_use
    )
    db.session.add(order)

    # Deduct redeemed points then award purchase points
    user.points = user.points - points_to_use + 50
    for item in items:
        db.session.delete(item)
    db.session.commit()
    session['user_points'] = user.points
    session['order_placed'] = {
        'grand': grand, 'points_used': points_to_use,
        'points_earned': 50, 'order_id': order.id
    }
    return redirect(url_for('order_success'))

@app.route('/order/success')
def order_success():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    order_data = session.pop('order_placed', None)
    user = User.query.get(session['user_id'])
    return render_template('order_success.html', order=order_data, user=user)

# ==============================================================================
# ROUTES — CHATBOT
# ==============================================================================

@app.route('/chatbot', methods=['POST'])
def chatbot():
    data    = request.get_json()
    message = data.get('message', '')
    user_name = session.get('user_name', 'friend')
    reply   = chatbot_response(message, user_name)
    # Award points for using chatbot (once per session)
    if 'user_id' in session and not session.get('chatbot_points_given'):
        award_points(session['user_id'], 5, "Health Consultation")
        session['chatbot_points_given'] = True
    return jsonify({'reply': reply})

# ==============================================================================
# ROUTES — POINTS / REDEEM
# ==============================================================================

@app.route('/points/redeem', methods=['POST'])
def redeem_points():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401
    # Handled at checkout; this is just a query endpoint
    user = User.query.get(session['user_id'])
    return jsonify({'points': user.points, 'tier': get_user_tier(user.points)})

# ==============================================================================
# ROUTES — LIFESTYLE, SCIENCE
# ==============================================================================

@app.route('/lifestyle')
def lifestyle():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user = User.query.get(session['user_id'])
    session['user_points'] = user.points
    return render_template('lifestyle.html', user=user, tier=get_user_tier(user.points))

@app.route('/science')
def science():
    return render_template('science.html')

# ==============================================================================
# CONTEXT PROCESSOR — available in all templates
# ==============================================================================

@app.context_processor
def inject_cart_count():
    count = 0
    if 'user_id' in session:
        count = db.session.query(db.func.sum(CartItem.quantity)).filter_by(
            user_id=session['user_id']).scalar() or 0
    return {'cart_count': int(count), 'session_points': session.get('user_points', 0)}

# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
