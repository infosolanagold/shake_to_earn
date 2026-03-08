import os
import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# CONNEXION MONGODB
try:
    MONGO_URI = os.environ.get('MONGODB_URI')
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.sgold_database
    users_col = db.users
    client.admin.command('ping')
    print("MongoDB Connected Successfully!")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

@app.route('/')
def home():
    return render_template('index.html')

# --- NOUVELLE ROUTE POUR LE LEADERBOARD ---
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    try:
        # On récupère les 10 meilleurs, triés par total_earned décroissant
        top_users = list(users_col.find({}, {"_id": 0, "wallet": 1, "total_earned": 1})
                         .sort("total_earned", -1)
                         .limit(10))
        return jsonify(top_users)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- LOGIQUE DE SHAKE ---
@app.route('/api/shake-earn', methods=['POST'])
def shake_earn():
    try:
        data = request.json
        wallet = data.get('walletAddress')
        check_only = data.get('checkOnly', False)
        
        if not wallet:
            return jsonify({"success": False, "message": "Wallet missing"}), 400

        user = users_col.find_one({"wallet": wallet})

        if not user:
            new_user = {"wallet": wallet, "last_shake": "", "total_earned": 0}
            users_col.insert_one(new_user)
            user = new_user

        if check_only:
            return jsonify({"success": True, "total_earned": user.get("total_earned", 0)})

        today_str = datetime.date.today().isoformat()
        if user.get("last_shake") == today_str:
            return jsonify({
                "success": False, 
                "message": "ALREADY SHAKEN TODAY!", 
                "total_earned": user.get("total_earned", 0)
            })

        reward = 500
        users_col.update_one(
            {"wallet": wallet},
            {"$set": {"last_shake": today_str}, "$inc": {"total_earned": reward}}
        )
        
        updated_user = users_col.find_one({"wallet": wallet})
        return jsonify({
            "success": True, 
            "amount": reward, 
            "total_earned": updated_user["total_earned"]
        })

    except Exception as e:
        return jsonify({"success": False, "message": "Server error"}), 500

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
