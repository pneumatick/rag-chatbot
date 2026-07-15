from flask import Flask

from chunking import Splitter, VectorInterface

server = Flask(__name__)

@server.route("/")
def testing():
    vec = VectorInterface()
    collection = vec.add_docs("user-docs")
    return collection.query(
        query_texts=["creativity"],
        n_results=3
    )

if __name__ == "__main__":
    server.run(host='0.0.0.0', port="5000", debug=True)