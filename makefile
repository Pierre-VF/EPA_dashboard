

.PHONY: run
run:
	streamlit run streamlit_app.py

.PHONY: uv_run
uv_run:
	uv run --with-requirements requirements.txt streamlit run streamlit_app.py