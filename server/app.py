from flask import Flask, json, jsonify, request
from pydantic import BaseModel, AnyHttpUrl
from datetime import datetime


class Image(BaseModel):
    url: AnyHttpUrl
    date: datetime


class ImageResponse(BaseModel):
    success: int
    data: list[Image]


app = Flask(__name__)
images: list[Image] = []

images.append(
    Image(
        url="https://cdn.discordapp.com/attachments/860987957363998751/862069898610999306/5556-stonks.png",
        date=datetime.today(),
    )
)


@app.route("/")
def hello_world():
    page = "<p>"
    for image in images:
        page += f"<img src={image.url} alt={image.date}>"
    page += "</p>"
    return page


@app.route("/api/v1/images", methods=["GET"])
def api_image_get():
    data = ImageResponse(success=True, data=images)

    response = app.response_class(
        response=data.json(),
        status=200,
        mimetype="application/json",
    )
    return response


@app.route("/api/v1/send_image", methods=["POST"])
def api_image_post():
    content = request.json
    images.append(Image(url=content["url"], date=datetime.today()))
    return {"received": True, "url": content["url"]}


if __name__ == "__main__":
    app.run(debug=True, host = '0.0.0.0')
