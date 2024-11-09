#!/bin/bash

SOURCE_FILE=$1
TARGET_FOLDER=$2
base_name=$(basename "$SOURCE_FILE")
target_folder=$TARGET_FOLDER/$base_name/
echo $target_folder $base_name $SOURCE_FILE
mkdir -p $target_folder
pdftoppm -jpeg -r 75 "$SOURCE_FILE" "$target_folder/page"
