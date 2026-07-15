from flask import Flask

from chunking import Splitter, VectorInterface

server = Flask(__name__)

@server.route("/")
def testing():
    vec = VectorInterface()
    (chunks, ids) = vec.add_docs("user-docs")
    return ids + chunks

if __name__ == "__main__":
    server.run(host='0.0.0.0', port="5000", debug=True)