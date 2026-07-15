from flask import Flask

from chunking import Splitter, chunk_docs

server = Flask(__name__)

@server.route("/")
def testing():
    return chunk_docs(Splitter.RECURSIVE)

if __name__ == "__main__":
    server.run(host='0.0.0.0', port="5000", debug=True)