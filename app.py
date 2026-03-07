import os
import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)

# --- CONFIGURATION CORS ---
CORS(app, resources={r"/api/*": {
    "origins": [
        "https://www.solanagoldguard.com", 
        "https://solanagoldguard.com", 
        "https://shake-to-earn.onrender.com"
    ]
}})

# 1. CONNEXION MONGODB
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

        # --- CONFIGURATION DES RÉCOMPENSES (Modifiable ici) ---
        BASE_REWARD = 500  # On est passé de 1000 à 500
        STREAK_BONUS = 50  # Bonus par jour de série

        if not user:
            # Premier shake pour ce wallet
            new_user = {
                "wallet": wallet,
                "last_shake": today_str,
                "streak": 1,
                "total_earned": BASE_REWARD
            }
            users_col.insert_one(new_user)
            return jsonify({
                "success": True, 
                "streak": 1, 
                "amount": BASE_REWARD,
                "total_earned": BASE_REWARD
            })

        # 3. VÉRIFICATION : DÉJÀ FAIT AUJOURD'HUI ?
        if user["last_shake"] == today_str:
            return jsonify({
                "success": False, 
                "message": "Already shaken today!",
                "total_earned": user.get("total_earned", 0)
            })

        # 4. CALCUL DU STREAK
        new_streak = 1
        if user["last_shake"] == yesterday_str:
            new_streak = user.get("streak", 1) + 1
        
        # Calcul de la récompense (500 + bonus)
        reward = BASE_REWARD + (new_streak * STREAK_BONUS)

        # 5. MISE À JOUR BASE
        users_col.update_one(
            {"wallet": wallet},
            {
                "$set": {"last_shake": today_str, "streak": new_streak},
                "$inc": {"total_earned": reward}
            }
        )

        # On récupère le nouveau total après mise à jour
        updated_user = users_col.find_one({"wallet": wallet})

        return jsonify({
            "success": True, 
            "streak": new_streak, 
            "amount": reward,
            "total_earned": updated_user["total_earned"]
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
