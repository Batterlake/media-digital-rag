.ONESHELL:
.PHONY: download-dataset

run:
	mkdir -p ./uploads
	mkdir -p ./logs
	touch ./logs/app.log
	tmux new-session -d -s web 'uvicorn app.main:app --host=0.0.0.0 --port=50001 --reload --reload-exclude logs* || bash'
	tmux attach -t web

stop:
	tmux kill-session -t web

download-dataset:
	mkdir -p ./data
	wget https://lodmedia.hb.bizmrg.com/case_files/1176378/train_dataset_mediawise_train.zip -O ./data/train_dataset_mediawise_train.zip
	cd ./data
	unzip train_dataset_mediawise_train.zip
	rm -r ./__MACOSX

convert-pdfs:
	cp data/train_data_mediawise/Media_Digital/* uploads/
	find uploads/ -type f -name '*.pdf' | xargs -I{} -P 40 -- ./tools/convert-pdf.sh {} ./previews/

populate-database:
	docker compose exec web bash -c 'poetry install && poetry run python tools/populate.py'

deploy:
	docker compose up -d

uvicorn:
	uvicorn app.main:app --reload --port 50004 --host 0.0.0.0 --workers 20
