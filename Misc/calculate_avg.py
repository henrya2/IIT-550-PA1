import argparse
import os
from pathlib import Path

def avg_one_file(file_name):
    avg_v = 0
    count = 0
    with open(file_name, "r") as fp:
        val = float(fp.readline())
        avg_v += val
        count += 1
    if count > 0:
        avg_v /= count

    return avg_v

if __name__ == "__main__":
    parser = argparse.ArgumentParser("Use calculate average!!!")
    parser.add_argument('file_or_folder', type=str, nargs='?')

    args = parser.parse_args()

    count = 0
    avg_v = 0
    file_or_folder = args.file_or_folder
    path = Path(file_or_folder)
    if path.is_dir():
        for x in path.iterdir():
            if x.is_file():
                val = avg_one_file(x)
                avg_v += val
                count += 1

    if count > 0:
            avg_v /= count

    print(avg_v)