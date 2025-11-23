"""
Module créant une invite de commande pour les opérations courantes
"""

import typer

from src.routines import alarme_quotidienne, compta

app = typer.Typer(name="EPA CLI", no_args_is_help=True)


@app.command()
def export_comptabilite_de_production():
    """
    Exporte les données de production de l'année passée, l'année en cours et aux dates anniversaires dans un fichier Excel
    """
    compta.export_comptabilite_de_production()


@app.command()
def verification_quotidienne():
    """
    Réalise une vérification quotidienne de la production de la veille
    """
    alarme_quotidienne.verification_quotidienne()
    print("Export terminé")


if __name__ == "__main__":
    app()
