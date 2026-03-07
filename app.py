import os
import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)

# --- CONFIGURATION CORS CRUCIALE ---
# On autorise explicitement tes deux domaines (avec et sans www) et ton lien de test Render
CORS(app, resources={r"/api/*": {
    "origins": [
        "https://www.solanagoldguard.com", 
        "https://solanagoldguard.com", 
        "https://shake-to-earn.onrender.com"
    ]
}})

# 1. CONNEXION MONGODB
# Assure-toi que la variable s'appelle bien MONGODB_URI dans Render
MONGO_URI = os.environ.get('MONGODB_URI')
client = MongoClient(MONGO_URI)
db = client.sgold_database
users_col = db.users

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/shake-earn', methods=['POST'])
def shake_earn():
    try:
        data = request.json
        wallet = data.get('walletAddress')
        
        if not wallet:
            return jsonify({"success": False, "message": "Wallet missing"}), 400

        # On récupère la date du jour
        today = datetime.date.today()
        today_str = today.isoformat()
        yesterday_str = (today - datetime.timedelta(days=1)).isoformat()

        # 2. RECHERCHE DE L'UTILISATEUR
        user = users_col.find_one({"wallet": wallet})

        if not user:
            # Premier shake pour ce wallet
            new_user = {
                "wallet": wallet,
                "last_shake": today_str,
                "streak": 1,
                "total_earned": 1000
            }
            users_col.insert_one(new_user)
            return jsonify({"success": True, "streak": 1, "amount": 1000})

        # 3. VÉRIFICATION : DÉJÀ FAIT AUJOURD'HUI ?
        if user["last_shake"] == today_str:
            return jsonify({"success": False, "message": "Already shaken today!"})

        # 4. CALCUL DU STREAK
        new_streak = 1
        if user["last_shake"] == yesterday_str:
            new_streak = user["streak"] + 1
        
        reward = 1000 + (new_streak * 100)

        # 5. MISE À JOUR BASE
        users_col.update_one(
            {"wallet": wallet},
            {
                "$set": {"last_shake": today_str, "streak": new_streak},
                "$inc": {"total_earned": reward}
            }
        )

        return jsonify({
            "success": True, 
            "streak": new_streak, 
            "amount": reward
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
