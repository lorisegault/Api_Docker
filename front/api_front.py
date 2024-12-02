from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import requests
import os

app = Flask(__name__)

API_SERVICE_URL = os.environ.get("API_SERVICE_URL", "http://back:5009")
AUTH_API_URL = os.environ.get("AUTH_API_URL", "http://auth:5008")


app.secret_key = "votre_cle_secrete"  


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            response = requests.post(
                f"{AUTH_API_URL}/token",
                data={"username": username, "password": password},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code == 200:
                token = response.json().get("access_token")
                # Stocker le token dans la session Flask
                session["token"] = token
                return redirect(url_for("accueil"))
            else:
                error_message = "Nom d'utilisateur ou mot de passe incorrect"
                return render_template("login.j2", error=error_message)

        except requests.exceptions.RequestException as e:
            error_message = f"Erreur lors de la connexion à l'API: {str(e)}"
            return render_template("login.j2", error=error_message)

    return render_template("login.j2")

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("token", None)
    return redirect(url_for("login"))

@app.before_request
def verify_token():
    exclude_path = ["/docs", "/openapi.json", "/redoc", "/login"]

    if request.path in exclude_path:
        return None

    token = session.get("token")  

    if not token:
        return redirect(url_for("login"))

    try:
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(f"{AUTH_API_URL}/users/me/", headers=headers)

        if response.status_code == 401:
            session.pop("token", None)
            return redirect(url_for("login"))
    except requests.exceptions.RequestException as e:
        return jsonify({"message": f"Erreur de service d'authentification: {str(e)}"}), 500



@app.route("/", methods=["GET", "POST"])
def accueil():
    if request.method == "POST":
        recherche_utilisateur = request.form.get("recherche_utilisateur")
        recherche_livre = request.form.get("recherche_livre")
        type_recherche = request.form.get("type_recherche")

        if type_recherche == "utilisateur" and recherche_utilisateur:
            return redirect(url_for("resultats", recherche=recherche_utilisateur, type_recherche="utilisateur"))
        elif type_recherche == "livre" and recherche_livre:
            return redirect(url_for("resultats", recherche=recherche_livre, type_recherche="livre"))
    
    return render_template("accueil.j2")

@app.route("/resultats", methods=["GET"])
def resultats():
    recherche = request.args.get("recherche")
    type_recherche = request.args.get("type_recherche")
    resultats = []

    # Récupérer le token depuis la session
    token = session.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    if type_recherche == "utilisateur":
        response = requests.get(f"{API_SERVICE_URL}/utilisateur/{recherche}", headers=headers)
        utilisateur = response.json()
        if isinstance(utilisateur, list):
            response = requests.get(f"{API_SERVICE_URL}/livres_full", headers=headers)
            livres = response.json()

            emprunts = [livre for livre in livres if livre["emprunteur_id"] == utilisateur[0]["id"]]
            utilisateur[0]["emprunts"] = emprunts
            resultats = [utilisateur[0]]
        else:
            response = requests.get(f"{API_SERVICE_URL}/utilisateurs", headers=headers)
            resultats = response.json()

            response = requests.get(f"{API_SERVICE_URL}/livres_full", headers=headers)
            livres = response.json()
            for utilisateur in resultats:
                emprunts = [livre for livre in livres if livre["emprunteur_id"] == utilisateur["id"]]
                utilisateur["emprunts"] = emprunts

    elif type_recherche == "livre":
        response = requests.get(f"{API_SERVICE_URL}/livres_full", headers=headers)
        livres = response.json()

        resultats = [livre for livre in livres if recherche.lower() in livre["titre"].lower() or str(livre["id"]) == recherche]
        
        if not resultats:
            resultats = livres

    return render_template("resultats.j2", resultats=resultats, type_recherche=type_recherche)

@app.route("/livres", methods=["GET"])
def livres():
    token = session.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    response = requests.get(f"{API_SERVICE_URL}/livres_full", headers=headers)
    livres = response.json()
    return render_template("livres.j2", livres=livres)

@app.route("/emprunts", methods=["GET"])
def emprunts():
    token = session.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    response = requests.get(f"{API_SERVICE_URL}/livres_full", headers=headers)
    livres = response.json()

    livres_empruntes = [livre for livre in livres if livre["emprunteur_id"] is not None]

    return render_template("emprunts.j2", livres=livres_empruntes)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
