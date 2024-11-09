.SILENT: run, stop, key

run:
	mkdir -p ./uploads
	mkdir -p ./logs
	touch ./logs/app.log
	tmux new-session -d -s web 'uvicorn app.main:app --host=0.0.0.0 --port=50041 --reload --reload-exclude logs* || bash'
	tmux attach -t web

stop:
	tmux kill -t web
