from flask import Flask, render_template, request, redirect, url_for
import requests
import os

app = Flask(__name__)

API_SERVICE_URL = os.environ.get("API_SERVICE_URL", "http://back:5009")

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

    if type_recherche == "utilisateur":
        response = requests.get(f"{API_SERVICE_URL}/utilisateur/{recherche}")
        utilisateur = response.json()
        print(utilisateur)
        if isinstance(utilisateur, list):
            response = requests.get(f"{API_SERVICE_URL}/livres_full")
            livres = response.json()

            emprunts = [livre for livre in livres if livre["emprunteur_id"] == utilisateur[0]["id"]]
            utilisateur[0]["emprunts"] = emprunts
            resultats = [utilisateur[0]]
        else:
            response = requests.get(f"{API_SERVICE_URL}/utilisateurs")
            resultats = response.json()

            response = requests.get(f"{API_SERVICE_URL}/livres_full")
            livres = response.json()
            print(resultats)
            for utilisateur in resultats:
                print(utilisateur)
                emprunts = [livre for livre in livres if livre["emprunteur_id"] == utilisateur["id"]]
                utilisateur["emprunts"] = emprunts           

    elif type_recherche == "livre":
        response = requests.get(f"{API_SERVICE_URL}/livres_full")
        livres = response.json()

        resultats = [livre for livre in livres if recherche.lower() in livre["titre"].lower() or str(livre["id"]) == recherche]
        
        if not resultats:
            resultats = livres

    return render_template("resultats.j2", resultats=resultats, type_recherche=type_recherche)

@app.route("/livres", methods=["GET"])
def livres():
    
    response = requests.get(f"{API_SERVICE_URL}/livres_full")
    livres = response.json()
    print(livres)
    return render_template("livres.j2", livres=livres)

@app.route("/emprunts", methods=["GET"])
def emprunts():
    response = requests.get(f"{API_SERVICE_URL}/livres_full")
    livres = response.json()

    livres_empruntes = [livre for livre in livres if livre["emprunteur_id"] is not None]

    return render_template("emprunts.j2", livres=livres_empruntes)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
