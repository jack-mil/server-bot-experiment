import time
from flask import Flask, render_template, request
from flask.wrappers import Response
import json

import queue


class MessageAnnouncer:
    """
    Utilize the really cool, blocking, threadsafe `queue.Queue`
    to dispach messages to clients across multiple threads.

    SSE functionality with Python Flask from this blog post:
    https://maxhalford.github.io/blog/flask-sse-no-deps/
    """

    def __init__(self) -> None:
        """
        Create a new `MessageAnnouncer` able to dispatch messages to any 'cients'
        that subscribe with a call to `.listen()`
        """
        self.listeners: list[queue.Queue] = []

    def listen(self) -> queue.Queue:
        """
        Subsribe to messages from this listener

        Returns a threadsafe, blocking `queue.Queue` which will be populated as messages come in
        """
        q = queue.Queue(maxsize=5)
        self.listeners.append(q)
        return q

    def announce(self, msg):
        """
        Dispatch a message to all listeners currently subscribed to this announcer

        If a client listener has not cleared recent messages,
        they will be unsubscribed from future announcments,
        and required to re subscribe with a call to `.listen()`
        """
        for i in range(len(self.listeners) - 1, -1, -1):
            # Loop in reverse order because listeners could be deleted
            try:
                # Attempt to 'send' the message without waiting.
                # If unable to do so, the listener is removed
                self.listeners[i].put_nowait(msg)
            except queue.Full:
                del self.listeners[i]


announcer = MessageAnnouncer()


def format_sse(data: str, event: str = None) -> str:
    """Format a message to be sent via SSE"""
    msg = f"data: {data}\n\n"
    if event is not None:
        msg = f"event: {event}\n{msg}"
    return msg


app = Flask(__name__)
images: list[dict] = []


TIME_FORMAT = "%Y-%m-%d-%H-%M-%S"
images.append(
    dict(
        url="https://cdn.discordapp.com/attachments/860987957363998751/862069898610999306/5556-stonks.png",
        date=time.strftime(TIME_FORMAT),
    )
)


@app.route("/")
def hello_world():
    return render_template('index.html')

@app.route('/ping')
def ping():
    msg = format_sse(data='pong')
    announcer.announce(msg=msg)
    return {"sse_sent": msg}, 200


@app.route("/stream/listen", methods=["GET"])
def msg_stream():
    """
    Stream events to the client using SSE
    https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events

    A thread blocking method, Flask must be using individual threads for each handled request
    This behavoir is default in recent versions.
    """
    # Not common to return a generator, but this Flask behavoir is documented here:
    # https://flask.palletsprojects.com/en/latest/patterns/streaming/
    def stream():
        messages = announcer.listen()  # Returns a Queue that will fill with messages
        while True:
            msg = messages.get()  # Blocks the thread until a new message has arrived
            yield msg

    # The "text/event-stream" MIME-type is special
    return Response(stream(), mimetype="text/event-stream")


@app.route("/api/v1/images", methods=["GET"])
def api_image_get():
    data = dict(success=True, data=images)
    return data


@app.route("/api/v1/send_image", methods=["POST"])
def api_image_post():
    # Get posted data
    content: dict = request.get_json()
    url = content.get("url")
    msg = content.get("text")
    msg_time = time.strftime(TIME_FORMAT)

    image_meta = dict(url=url, message=msg, date=msg_time)

    # Save posted messages locally
    images.append(image_meta)
    # And also format for SSE client
    sse_msg = format_sse(event="new_msg", data=json.dumps(image_meta))

    # Add SSE message to be streamed to client
    # See msg_stream() method
    announcer.announce(sse_msg)

    return {"received": True, "url": content["url"]}


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
