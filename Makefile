.PHONY: up down up-ml up-full logs ml-logs db-shell migrate migration seed seed-kg test-api test-web lint clean warm-model ml-health

up:
	docker compose up -d

down:
	docker compose down

up-ml:
	docker compose --profile ml up -d

up-full:
	docker compose --profile ml up -d

logs:
	docker compose logs -f

ml-logs:
	docker compose --profile ml logs -f ml

db-shell:
	docker compose exec db psql -U medbed -d medbed

migrate:
	docker compose exec api alembic upgrade head

migration:
	docker compose exec api alembic revision --autogenerate -m "$(msg)"

seed:
	docker compose exec api python -m app.seed

seed-kg:
	docker compose exec api python -m app.seed_knowledge_graph

test-api:
	docker compose exec api pytest -v

test-web:
	docker compose exec web npm test

lint:
	docker compose exec api ruff check .
	docker compose exec web npm run lint

clean:
	docker compose down -v
	rm -rf api/__pycache__ api/app/__pycache__

warm-model:
	@echo "Warming up ML model (first call downloads ~600MB)..."
	@curl -s -X POST http://localhost:8001/embed \
		-H "Content-Type: application/json" \
		-d '{"texts": ["ANAEMIA, located at BODY OF MAN, deviation score 0.188"]}' \
		--max-time 600 | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Model: {d[\"model\"]}, Dimension: {d[\"dimension\"]}, Count: {d[\"count\"]}')"
	@echo "Model warmed successfully."

ml-health:
	@curl -s http://localhost:8001/health | python3 -m json.tool
