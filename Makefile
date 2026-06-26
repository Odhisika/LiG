.PHONY: audit vulns check deploy

audit:
	@echo "Running full security audit..."
	@./scripts/security-audit.sh

vulns:
	@echo "Scanning dependency vulnerabilities..."
	@pip-audit

check:
	@python manage.py check

deploy:
	@python manage.py check --deploy
