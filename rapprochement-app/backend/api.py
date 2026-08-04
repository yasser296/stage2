from pathlib import Path
import shutil
from uuid import uuid4, UUID

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from config import SAA_ZIP, D_SOURCE
from processing import (
    CATEGORIES,
    run_comparison,
    clear_sources_cache,
)

app = FastAPI(title="Rapprochement SAA / D")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS_DIRECTORY = Path(__file__).parent / "runs"

def clear_old_runs():
    RUNS_DIRECTORY.mkdir(exist_ok=True)

    for item in RUNS_DIRECTORY.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()


def count_files(path: Path):
    if path.is_file():
        return 1

    if path.is_dir():
        return sum(
            1 for file in path.rglob("*")
            if file.is_file()
        )

    return 0


@app.get("/api/status")
def get_status():
    """Vérifie que les deux sources existent."""

    return {
        "saa": {
            "name": SAA_ZIP.name,
            "exists": SAA_ZIP.is_file(),
        },
        "d": {
            "name": "Dossier D",
            "exists": D_SOURCE.exists(),
            "files": count_files(D_SOURCE),
        },
        "categories": CATEGORIES,
    }


@app.post("/api/compare")
def compare(category: str | None = None):
    """Lance le rapprochement sans recevoir de fichier."""

    selected_category = category.strip() if category else None

    if selected_category and selected_category not in CATEGORIES:
        raise HTTPException(
            status_code=400,
            detail=f"Categorie inconnue : {selected_category}",
        )

    if not SAA_ZIP.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Archive SAA introuvable : {SAA_ZIP}",
        )

    if not D_SOURCE.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Source D introuvable : {D_SOURCE}",
        )

    clear_old_runs()
    job_id = str(uuid4())
    output_directory = RUNS_DIRECTORY / job_id

    try:
        result = run_comparison(output_directory, selected_category)
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    result["jobId"] = job_id
    result["reportUrl"] = f"/api/reports/{job_id}"

    return result


@app.post("/api/reload-sources")
def reload_sources():
    """
    À appeler lorsque SAA.zip ou le dossier D est remplacé.
    """
    clear_sources_cache()

    return {
        "message": "Les fichiers seront relus au prochain rapprochement."
    }


@app.get("/api/reports/{job_id}")
def download_report(job_id: str):
    """Télécharge le rapport produit par compare_and_save()."""

    try:
        UUID(job_id)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Identifiant de rapport invalide.",
        )

    report = (
        RUNS_DIRECTORY
        / job_id
        / "Rapprochement_SAA_vs_D.txt"
    )

    if not report.is_file():
        raise HTTPException(
            status_code=404,
            detail="Rapport introuvable.",
        )

    return FileResponse(
        path=report,
        filename="Rapprochement_SAA_vs_D.txt",
        media_type="text/plain",
    )
