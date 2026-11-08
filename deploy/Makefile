INVENTORY := metatron,

.PHONY: all backend frontend

all: backend frontend

backend:
	cd backend && ansible-playbook -i $(INVENTORY) playbook_backend.yaml

frontend:
	cd frontend && ansible-playbook -i $(INVENTORY) playbook_frontend.yaml
