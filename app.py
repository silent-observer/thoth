import os
from flask import Flask, g
from neo4j import GraphDatabase

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

neo4j_pass = os.environ.get('NEO4J_PASS')
neo4j_uri = 'neo4j+s://1f59f68c.databases.neo4j.io'

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = GraphDatabase.driver(
            neo4j_uri, auth=('neo4j', neo4j_pass))
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route("/")
def hello_world():
    names = []
    with get_db().session() as session:
        result = session.run('MATCH (n:Person) RETURN n')
        for r in result:
            names.append(r['n']['name'])
    return "<p>People:<br>" + '<br>'.join(names) + "</p>"