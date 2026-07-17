from flask import Flask

from chunking import VectorInterface

server = Flask(__name__)

@server.route("/")
def testing():
    vec = VectorInterface()
    #vec.add_docs("user-docs")
    return vec.query("What novel insights can be gained from my writings on creativity?").choices[0].message.content

if __name__ == "__main__":
    server.run(host='0.0.0.0', port="5000", debug=True)