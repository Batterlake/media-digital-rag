.SILENT: run, stop, key

run:
	mkdir -p ./uploads
	tmux new-session -d -s web 'uvicorn app.main:app --host=0.0.0.0 --port=50045 --reload --reload-exclude logs* || bash' tmux
	tmux attach -t web

stop:
	tmux kill -t web
