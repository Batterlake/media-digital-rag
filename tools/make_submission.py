import argparse
from pathlib import Path

import pandas as pd
from tqdm import tqdm

from app.db import colpali_client, vector_search
from app.llm import request_with_image


def parse_argse():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-s",
        "--source",
        dest="source",
        required=True,
        help="Source xlsx file with questions",
    )
    parser.add_argument(
        "-t",
        "--target",
        dest="target",
        default="submission.csv",
        help="Output file with answers",
    )
    parser.add_argument(
        "-d",
        "--datadir",
        dest="datadir",
        default="data/jpeg",
        help="directory with slices pdf slides",
    )
    return parser.parse_args()


def main(args):
    submisson = pd.DataFrame(columns=("question", "answer", "filename", "slide_number"))
    questions = pd.read_excel(args.source)["question"]
    answers = []
    file_ids = []
    page_ids = []
    for q in tqdm(questions):
        multivector_query = colpali_client.embed_texts([q])[0]
        matches = vector_search(multivector_query, 10)[0]
        file_id = matches["file_id"].split("/")[1]
        page_id = matches["page_id"]
        filename = Path(f"{args.datadir}/{file_id}.pdf/page-{page_id}.jpg")
        answer = request_with_image(q, filename)

        answers.append(answer)
        file_ids.append(file_id)
        page_ids.append(page_id)
    submisson = pd.DataFrame(
        {
            "question": questions,
            "answer": answers,
            "filename": file_ids,
            "slide_number": page_ids,
        }
    )
    submisson.to_csv(args.target, sep=",", index=False)


if __name__ == "__main__":
    args = parse_argse()
    main(args)
