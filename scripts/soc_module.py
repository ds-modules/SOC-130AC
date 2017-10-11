import pandas as pd
import os


def download_images(table):
    for index, row in table.iterrows():
        census_tract = row["Census Tract"]
        urls = row["Images"].split(", ")
        for u in urls:
            fid = u.split("id=")[-1]
            os.system(
                "curl -L -o images/{}.jpg 'https://drive.google.com/uc?export=download&id={}'".format(
                    str(census_tract) + "---" + fid, fid))


def html_popup(title, comment, imgpath, data):
    html = """
    <h3>TITLE</h3>
    <img
       src = IMGPATH
       style="width:180px;height:128px;"
       >
    <p>
       "COMMENT"
    </p>
    <p>
       DATA
    </p>
    """

    html = html.replace(
        "TITLE",
        title).replace(
        "COMMENT",
        comment).replace(
            "IMGPATH",
            imgpath).replace(
                "DATA",
        data)

    return html
