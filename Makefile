.ONESHELL:

download-dataset:
	mkdir -p ./data
	wget https://lodmedia.hb.bizmrg.com/case_files/1176378/train_dataset_mediawise_train.zip -O ./data/train_dataset_mediawise_train.zip
	cd ./data
	unzip train_dataset_mediawise_train.zip
	rm -r ./__MACOSX