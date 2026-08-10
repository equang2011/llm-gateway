.PHONY: run check

run:
	uvicorn app.app:app --reload

check:
	ruff format --check .
	ruff check .
	pytest