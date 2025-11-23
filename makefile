

run:
	uv run streamlit run streamlit_app.py

clear_cache:
	rm .data/*.pkl

install:
	uv sync --all-groups

code_cleanup:
	uv tool run pre-commit install
	uv tool run pre-commit run --all

# Kept for backwards compatibility
.PHONY: uv_run
uv_run:
	uv run streamlit run streamlit_app.py
