

.PHONY: run
run:
	uv run streamlit run streamlit_app.py

.PHONY: clear_cache
clear_cache:
	rm .data/*.pkl

# Kept for backwards compatibility
.PHONY: uv_run
uv_run:
	uv run streamlit run streamlit_app.py