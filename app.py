import os
import time  # NÉCESSAIRE POUR LE CHRONOMÈTRE STRICT
import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# CONNEXION MONGODB
try:
    MONGO_URI = os.environ.get('MONGODB_URI')
    # L'ajout de connect=False est VITAL ici. Il empêche le serveur de geler sur Render !
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000, connect=False)
    db = client.sgold_database
    users_col = db.users
    print("MongoDB Ready!")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

@app.route('/')
def home():
    return render_template('index.html')

# --- NOUVELLE ROUTE POUR AFFICHER LA PAGE ADMIN ---
@app.route('/admin')
def admin_page():
    return render_template('admin.html')

# --- ROUTE POUR LE LEADERBOARD ---
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        # On récupère tout le monde (sans limite de 10) pour que l'admin puisse tous les payer
        top_users = list(users_col.find({}, {"_id": 0, "wallet": 1, "total_earned": 1})
                         .sort("total_earned", -1))
        return jsonify(top_users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- LOGIQUE DE SHAKE (SÉCURITÉ MAXIMUM 24H) ---
@app.route('/api/shake-earn', methods=['POST'])
def shake_earn():
    try:
        data = request.json
        wallet = data.get('walletAddress')
        check_only = data.get('checkOnly', False)
        
        if not wallet:
            return jsonify({"success": False, "message": "Wallet missing"}), 400

        user = users_col.find_one({"wallet": wallet})

        # Création de l'utilisateur s'il n'existe pas
        if not user:
            new_user = {"wallet": wallet, "last_shake_ts": 0, "total_earned": 0}
            users_col.insert_one(new_user)
            user = new_user

        if check_only:
            return jsonify({"success": True, "total_earned": user.get("total_earned", 0)})

        # --- VÉRIFICATION DU TEMPS STRICTE ---
        now_ts = time.time()
        last_shake_ts = user.get("last_shake_ts", 0)

        # 86400 secondes = exactement 24 heures
        if (now_ts - last_shake_ts) < 86400:
            time_left = int(86400 - (now_ts - last_shake_ts))
            hours = time_left // 3600
            minutes = (time_left % 3600) // 60
            
            # ARRÊT IMMÉDIAT : On ne distribue pas de récompense
            return jsonify({
                "success": False, 
                "message": f"WAIT {hours}H {minutes}M", 
                "total_earned": user.get("total_earned", 0)
            })

        # --- DISTRIBUTION DE LA RÉCOMPENSE ---
        reward = 500
        
        # Mise à jour atomique : on change le timestamp ET on incrémente le gain
        result = users_col.update_one(
            {"wallet": wallet},
            {"$set": {"last_shake_ts": now_ts}, "$inc": {"total_earned": reward}}
        )
        
        if result.modified_count > 0:
            updated_user = users_col.find_one({"wallet": wallet})
            return jsonify({
                "success": True, 
                "amount": reward, 
                "total_earned": updated_user["total_earned"]
            })
        else:
            return jsonify({"success": False, "message": "Update failed"}), 500

    except Exception as e:
        print(f"Server error: {e}")
        return jsonify({"success": False, "message": "Server error"}), 500

# --- ROUTE SECRÈTE POUR RÉINITIALISER UN JOUEUR (ADMIN) ---
@app.route('/api/admin/reset-user', methods=['POST'])
def reset_user():
    data = request.json
    password = data.get('password')
    wallet = data.get('wallet')

    # MOT DE PASSE ADMIN
    if password != "admin2026": 
        return jsonify({"success": False, "message": "Access Denied"}), 401

    if not wallet:
        return jsonify({"success": False, "message": "No wallet provided"}), 400

    # Remet le compteur du joueur à ZÉRO
    users_col.update_one(
        {"wallet": wallet},
        {"$set": {"total_earned": 0}}
    )
    
    return jsonify({"success": True, "message": f"Compteur de {wallet} remis à 0 !"})

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
