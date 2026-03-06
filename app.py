import os
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    # C'est ici que ton site s'affichera
    return render_template('index.html')

@app.route('/api/shake-earn', methods=['POST'])
def shake_earn():
    data = request.json
    wallet = data.get('walletAddress')
    
    # Pour le test avant d'ajouter la DB et Solana :
    print(f"Shake reçu de : {wallet}")
    return jsonify({
        "success": True, 
        "message": "Shake détecté !", 
        "streak": 1,
        "amount": 1000
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
