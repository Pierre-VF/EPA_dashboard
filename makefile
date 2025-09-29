

.PHONY: run
run:
	uv run streamlit run streamlit_app.py

# Kept for backwards compatibility
.PHONY: uv_run
uv_run:
	uv run streamlit run streamlit_app.py