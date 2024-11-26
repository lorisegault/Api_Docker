# Ou bien pour génération automatique : Code en FastAPI

import sqlite3
from fastapi import FastAPI, HTTPException, Path, Body
from typing import Union, Callable, Annotated
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import random
import json
import time
import pathlib
import os

path_to_db = pathlib.Path(__file__).parent.absolute() /"data" / "database.db"


class Utilisateur(BaseModel):
    id: int
    nom: str
    email: str
    def __init__(self, id, nom, email):
        super().__init__(id=id, nom=nom, email=email)

# Votre code ici...


# .....................................................................
app = FastAPI()


@app.get("/")
async def index():
    return JSONResponse(content="Bienvenue sur cette API", status_code=200)


@app.get("/utilisateurs", response_model=list[Utilisateur])
async def recup_utilisateurs():

    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM utilisateurs")
        resultat_utilisateurs = cur.fetchall()

        utilisateurs_dico = [{"id": utilisateur[0], "nom": utilisateur[1], "email": utilisateur[2]} 
                             for utilisateur in resultat_utilisateurs]

    return JSONResponse(content=utilisateurs_dico, status_code=200)

@app.get("/livres")
async def recup_livres():
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                livres.id, 
                livres.nom, 
                livres.titre, 
                livres.pitch, 
                livres.auteur_id, 
                livres.date_public, 
                livres.emprunteur_id,
                utilisateurs.nom AS emprunteur_nom
            FROM livres
            LEFT JOIN utilisateurs ON livres.emprunteur_id = utilisateurs.id

        """)
        resultat_livres = cur.fetchall()

        livres_dico = [
            {
                "id": livre[0],
                "nom": livre[1],
                "titre": livre[2],
                "pitch": livre[3],
                "auteur_id": livre[4],
                "date_public": livre[5],
                "emprunteur_id": livre[6],
            }
            for livre in resultat_livres
        ]

    return JSONResponse(content=livres_dico, status_code=200)


@app.get("/livres_full")
async def recup_livres_full():
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                livres.id, 
                livres.nom, 
                livres.titre, 
                livres.pitch, 
                livres.auteur_id, 
                livres.date_public, 
                livres.emprunteur_id,
                utilisateurs.nom AS emprunteur_nom,
                auteurs.nom_auteurs AS auteurs_nom
            FROM livres
            LEFT JOIN utilisateurs ON livres.emprunteur_id = utilisateurs.id
            LEFT JOIN auteurs ON livres.auteur_id = auteurs.id
        """)

        resultat_livres = cur.fetchall()

        livres_dico = [
            {
                "id": livre[0],
                "nom": livre[1],
                "titre": livre[2],
                "pitch": livre[3],
                "auteur_id": livre[4],
                "date_public": livre[5],
                "emprunteur_id": livre[6],
                "emprunteur_nom": livre[7],
                "auteur_nom": livre[8],

            }
            for livre in resultat_livres
        ]

    return JSONResponse(content=livres_dico, status_code=200)

@app.get("/auteurs")
async def recup_auteurs():
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM auteurs")
        resultat_auteurs = cur.fetchall()

        auteurs_dico = [
            {"id": auteur[0], "nom_auteurs": auteur[1]} for auteur in resultat_auteurs
        ]

    return JSONResponse(content=auteurs_dico, status_code=200)



@app.get("/utilisateur/{utilisateur}")
async def recup_utilisateur_par_id_nom(utilisateur: str):
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()

        try:
            id_utilisateur = int(utilisateur)
            cur.execute("SELECT * FROM utilisateurs WHERE id = ?", (id_utilisateur,))
        except ValueError:
            cur.execute("SELECT * FROM utilisateurs WHERE nom = ?", (utilisateur,))
        
        resultat = cur.fetchall()

        if len(resultat) > 1:
            raise HTTPException(
                status_code=400,
                detail=f"Impossible : il existe plusieurs utilisateurs portant le nom '{utilisateur}'."
            )
        if len(resultat) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Impossible : aucun utilisateur '{utilisateur}' trouvé."
            )

        utilisateur_dico = [
            {"id": utilisateur[0], "nom": utilisateur[1], "email": utilisateur[2]}
            for utilisateur in resultat
        ]

    return JSONResponse(content=utilisateur_dico, status_code=200)

@app.get("/utilisateur/emprunts/{utilisateur}")
async def recup_emprunts_utilisateur_par_id_nom(utilisateur: str):
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()

        try:
            id_utilisateur = int(utilisateur)
            cur.execute("SELECT * FROM livres WHERE emprunteur_id = ?", (id_utilisateur,))
            resultat = cur.fetchall()
        except ValueError:
            cur.execute("SELECT id FROM utilisateurs WHERE nom = ?", (utilisateur,))
            resultat = cur.fetchall()

            if len(resultat) > 1:
                raise HTTPException(
                    status_code=400,
                    detail=f"Impossible : il existe plusieurs utilisateurs portant le nom '{utilisateur}'."
                )
            elif len(resultat) == 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Impossible : aucun utilisateur '{utilisateur}' trouvé."
                )
            else:
                utilisateur_id = resultat[0][0]
                cur.execute("SELECT * FROM livres WHERE emprunteur_id = ?", (utilisateur_id,))
                resultat = cur.fetchall()

        if len(resultat) == 0:
            raise HTTPException(
                status_code=400,
                detail="Impossible : aucun emprunt trouvé pour cet utilisateur."
            )

        emprunt_dico = [
            {
                "id": livre[0],
                "nom": livre[1],
                "titre": livre[2],
                "pitch": livre[3],
                "auteur_id": livre[4],
                "date_public": livre[5],
                "emprunteur_id": livre[6],
            }
            for livre in resultat
        ]

    return JSONResponse(content=emprunt_dico, status_code=200)



@app.get("/livres/siecle/{numero}")
async def recup_livres_siecles(numero: int):
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM livres")

        resultat = cur.fetchall()

        livres_dico = []
        for livre in resultat:
            date_public_annee = time.strptime(livre[5], "%d/%m/%Y")
            date_public_siecle = (date_public_annee.tm_year - 1) // 100 + 1

            if date_public_siecle == numero:
                livres_dico.append(
                    {
                        "id": livre[0],
                        "nom": livre[1],
                        "titre": livre[2],
                        "pitch": livre[3],
                        "auteur_id": livre[4],
                        "date_public": livre[5],
                        "emprunteur_id": livre[6],
                    }
                )

        if len(livres_dico) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Impossible : aucun livre ne correspond au siècle {numero}.",
            )

    return JSONResponse(content=livres_dico, status_code=200)

class Livre(BaseModel):
    author: str
    title: str
    content: str
    date: str

@app.post("/livres/ajouter")
async def ajouter_livres(livre: Livre):
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()

       
        cur.execute("SELECT * FROM auteurs")
        resultat = cur.fetchall()
        for auteur in resultat:
            if str(auteur[1]) == livre.author: 
                cur.execute(
                    """
                    INSERT INTO livres (nom, titre, pitch, auteur_id, date_public, emprunteur_id)
                    VALUES (?, ?, ?, ?, ?, NULL)
                    """,
                    (livre.author, livre.title, livre.content, auteur[0], livre.date),
                )

                conn.commit()

                return JSONResponse(
                    content={"message": "Nouveau livre ajouté avec succès."}, status_code=200
                )

        cur.execute("INSERT INTO auteurs (nom_auteurs) VALUES (?)", (livre.author,))
        conn.commit()
        for auteur in resultat:
            if str(auteur[1]) == livre.author: 
                cur.execute(
                    """
                    INSERT INTO livres (nom, titre, pitch, auteur_id, date_public, emprunteur_id)
                    VALUES (?, ?, ?, ?, ?, NULL)
                    """,
                    (livre.author, livre.title, livre.content, auteur[0], livre.date),
                )

                conn.commit()

                return JSONResponse(
                    content={"message": "Nouveau livre ajouté avec succès."}, status_code=200
                )

    return JSONResponse(
        content={"message": "Nouveau livre et auteur ajoutés avec succès."}, status_code=200
    )


class UtilisateurAjout(BaseModel):
    nom: str
    email: str

@app.post("/utilisateur/ajouter")
async def ajouter_utilisateur(utilisateur: UtilisateurAjout):
    
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO utilisateurs (nom, email) VALUES (?, ?)",
            (utilisateur.nom, utilisateur.email),
        )
        conn.commit()
    return {"message": "Nouveau utilisateur ajouté avec succès"}
 
@app.delete("/utilisateur/{utilisateur}/supprimer")
async def supprimer_utilisateur(utilisateur: str):
    
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()

        try:
            utilisateur_id = int(utilisateur)
            cur.execute("SELECT * FROM utilisateurs WHERE id = ?", (utilisateur_id,))
            resultat = cur.fetchall()

            cur.execute("DELETE FROM utilisateurs WHERE id = ?", (utilisateur_id,))

        except ValueError:
            cur.execute("SELECT * FROM utilisateurs WHERE emprunteur_id = ?", (utilisateur,))
            resultat = cur.fetchall()

            cur.execute("DELETE FROM utilisateurs WHERE nom = ?", (utilisateur,))

        if len(resultat) == 0:
            return JSONResponse(
                status_code=400,
                content={"message": "Utilisateur introuvé"}
            )

        conn.commit()
        return JSONResponse(
            status_code=200,
            content={"message": "Utilisateur supprimé avec succès"}
        )

@app.put("/utilisateur/{utilisateur_id}/emprunter/{livre_id}")
async def ajouter_emprunt(utilisateur_id: int, livre_id: int):
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM livres WHERE id = ?", (livre_id,))
        livre = cur.fetchall()

        if len(livre) == 0:
            return JSONResponse(
                status_code=400,
                content={"message": "Livre introuvable"}
            )

        cur.execute("SELECT * FROM utilisateurs WHERE id = ?", (utilisateur_id,))
        utilisateur = cur.fetchall()

        if len(utilisateur) == 0:
            return JSONResponse(
                status_code=400,
                content={"message": "Utilisateur introuvable"}
            )

        cur.execute("UPDATE livres SET emprunteur_id = ? WHERE id = ?", (utilisateur_id, livre_id))
        conn.commit()

        return JSONResponse(
            status_code=200,
            content={"message": f"Livre {livre_id} emprunté par {utilisateur_id} OK"}
        )
    
@app.put("/utilisateur/{utilisateur_id}/rendre/{livre_id}")
async def rendre_emprunt(utilisateur_id: int, livre_id: int):
    with sqlite3.connect(path_to_db) as conn:
        cur = conn.cursor()

        cur.execute("SELECT * FROM utilisateurs WHERE id = ?", (utilisateur_id,))
        utilisateur = cur.fetchall()

        if len(utilisateur) == 0:
            return JSONResponse(
                status_code=400,
                content={"message": "Utilisateur introuvable"}
            )

        cur.execute("SELECT * FROM livres WHERE id = ?", (livre_id,))
        livre = cur.fetchall()

        if len(livre) == 0:
            return JSONResponse(
                status_code=400,
                content={"message": "Livre introuvable"}
            )

        if livre[0][6] != utilisateur_id:
            return JSONResponse(
                status_code=400,
                content={"message": "Pas d'emprunt trouvé correspondant à ce livre et cet utilisateur"}
            )

        cur.execute("UPDATE livres SET emprunteur_id = NULL WHERE id = ?", (livre_id,))
        conn.commit()

        return JSONResponse(
            status_code=200,
            content={"message": f"Livre {livre_id} rendu par {utilisateur_id} OK"}
        )

import uvicorn
if __name__ == '__main__':
    # uvicorn.run(app, host='localhost', port=5009)
    # code pour lancer depuis un notebook Jupyter
    import nest_asyncio
    nest_asyncio.apply()
    uvicorn.run(app, host='0.0.0.0', port=5009)