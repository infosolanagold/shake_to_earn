import os
import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# CONNEXION MONGODB
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
        check_only = data.get('checkOnly', False)
        
        if not wallet:
            return jsonify({"success": False, "message": "Wallet missing"}), 400

        user = users_col.find_one({"wallet": wallet})

        # Si l'utilisateur n'existe pas encore
        if not user:
            if check_only:
                return jsonify({"success": True, "total_earned": 0})
            
            # Création du premier profil
            new_user = {
                "wallet": wallet,
                "last_shake": "",
                "total_earned": 0
            }
            users_col.insert_one(new_user)
            user = new_user

        # Si c'est juste pour vérifier le solde (au chargement)
        if check_only:
            return jsonify({"success": True, "total_earned": user.get("total_earned", 0)})

        # LOGIQUE DE SHAKE (24h)
        today_str = datetime.date.today().isoformat()
        if user.get("last_shake") == today_str:
            return jsonify({
                "success": False, 
                "message": "ALREADY SHAKEN TODAY!", 
                "total_earned": user.get("total_earned", 0)
            })

        # MISE À JOUR : +500 SGOLD
        reward = 500
        users_col.update_one(
            {"wallet": wallet},
            {
                "$set": {"last_shake": today_str},
                "$inc": {"total_earned": reward}
            }
        )
        
        # Récupération du nouveau total
        updated_user = users_col.find_one({"wallet": wallet})
        
        return jsonify({
            "success": True, 
            "amount": reward, 
            "total_earned": updated_user["total_earned"]
        })

    except Exception as e:
        print(f"Server Error: {e}")
        return jsonify({"success": False, "message": "Database Error"}), 500
