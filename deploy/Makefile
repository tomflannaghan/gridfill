INVENTORY := coultershaw_server,

.PHONY: all backend nginx frontend

all: backend nginx frontend

backend:
	cd backend && ansible-playbook -i $(INVENTORY) playbook_backend.yaml

nginx:
	cd nginx && ansible-playbook -i $(INVENTORY) playbook_nginx.yaml

frontend:
	cd frontend && ansible-playbook -i $(INVENTORY) playbook_frontend.yaml
