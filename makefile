

run:
	uv run streamlit run streamlit_app.py

clear_cache:
	rm .data/*.pkl

install:
	uv sync --all-groups

code_cleanup:
	uv tool run pre-commit install
	uv tool run pre-commit run --all

cli:
	uv run src/routines/__init__.py

cli_journalier:
	uv run src/routines/alarme_quotidienne.py

cli_export_comptabilite:
	uv run src/routines/compta.py


# Pour rétrocompatibilité
.PHONY: uv_run
uv_run:
	uv run streamlit run streamlit_app.py
