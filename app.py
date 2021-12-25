import os, string
from flask import Flask, g, request, session, render_template, abort
from flask.helpers import url_for
from neo4j import GraphDatabase, unit_of_work
from neo4j.time import Date, DateTime

import bcrypt, base64
from werkzeug.utils import redirect
import random, atexit
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import timedelta

neo4j_pass = os.environ.get('NEO4J_PASS')
neo4j_uri = 'neo4j+s://1f59f68c.databases.neo4j.io'

def update_recommendations():
    with GraphDatabase.driver(neo4j_uri, auth=('neo4j', neo4j_pass)) as local_db:
        with local_db.session() as db:
            db.run(r'''
                MATCH (a:Question)<-[:VIEWED]-(u:User)-[:VIEWED]->(b:Question)
                WHERE id(a) < id(b) AND (a.needs_update OR b.needs_update)
                WITH a, b, count(u) as aAndB
                WITH a, b, aAndB, toFloat(aAndB)/toFloat(a.views+b.views-aAndB) as j
                WHERE j > 0.15
                MERGE (a)-[s:SIMILAR]-(b)
                SET s.jaccard = j, a.needs_update = false, b.needs_update = false;
            ''')
            print('Updated recommendations!')

def delete_expired_data():
    with GraphDatabase.driver(neo4j_uri, auth=('neo4j', neo4j_pass)) as local_db:
        with local_db.session() as db:
            result = db.run(r'''
                MATCH (n)<-[r:HIDDEN]-(u:User:Moderator)
                WHERE r.date < datetime()
                MATCH (n)<-[:TO*0..]-(x)
                DETACH DELETE x
                RETURN count(x) as c
            ''').single()
            print(f'Deleted {result["c"]} objects!')

sched = BackgroundScheduler(daemon=True)
sched.add_job(update_recommendations, 'interval', minutes=60)
sched.add_job(delete_expired_data, 'interval', days=1)
sched.start()

atexit.register(lambda: sched.shutdown(wait=False))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')

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
def main():
    logged_in = 'username' in session
    username = session.get('username')
    with get_db().session() as db:
        questions = []
        if logged_in:
            result = db.run(r'''
                MATCH (u:User {username:"admin"})
                CALL {
                    WITH u
                    MATCH (u)-[v:VIEWED]->(qv:Question)
                    MATCH (qv)-[s:SIMILAR]-(qs:Question)
                    WHERE NOT ()-[:HIDDEN]->(qs)
                    RETURN qs, sum(s.jaccard) as j

                    UNION

                    MATCH (qs:Question)
                    WHERE NOT ()-[:HIDDEN]->(qs)
                    WITH qs, duration.inSeconds(qs.date, datetime()).seconds as secondsPast
                    RETURN qs, (qs.views + qs.rating * 2 + 50.0 / (1.0 + 0.00001 * secondsPast)) / 500 as j
                }
                WITH DISTINCT qs, j
                MATCH (a:User)-[:ASKED]->(qs)-[:CORRESPONDS]->(d:Discipline)
                OPTIONAL MATCH (u)-[viewed:VIEWED]->(qs)
                OPTIONAL MATCH (u)-[voted:VOTED]->(qs)
                RETURN a, qs, d, CASE
                    WHEN viewed IS NULL THEN j * 2
                    ELSE j
                END as j
                ORDER BY j DESC
                LIMIT 50''', username=username
            )
        else:
            result = db.run(r'''
                MATCH (qs:Question)
                WHERE NOT ()-[:HIDDEN]->(qs)
                WITH qs, duration.inSeconds(qs.date, datetime()).seconds as secondsPast
                WITH qs, qs.views + qs.rating * 2 + 50.0 / (1.0 + 0.00001 * secondsPast) as j
                MATCH (a:User)-[:ASKED]->(qs)-[:CORRESPONDS]->(d:Discipline)
                RETURN a, qs, d, j
                ORDER BY j DESC
                LIMIT 50'''
            )
        for r in result:
            questions.append({
                'id': r['qs']['id'],
                'title': r['qs']['title'],
                'text': r['qs']['question'],
                'date': r['qs']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
                'rating': r['qs']['rating'],
                'current_vote': r['voted']['vote'] if 'voted' in r and r['voted'] is not None else 0,
                'author': {'name': r['a']['username'], 'rating': r['a']['rating']},
                'discipline': r['d']['name']
            })

        data = {
            'questions': questions
        }
    return render_template('feed.html', data=data, logged_in=logged_in, my_name=username)

cyrillic_letters = 'АаБбВвГгДдЕеЁёЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЫыЬьЭэЮюЯя'

allowed_username_characters = set(
    string.ascii_letters + string.digits + '.-_'
)
allowed_password_characters = set(
    string.ascii_letters + cyrillic_letters + string.digits + '!@#$;%^:&?*()_-+=\'"'
)

def is_username_valid(username):
    return (len(username) >= 4 and len(username) <= 20 and
        set(username) <= allowed_username_characters)
def is_password_valid(password):
    return (len(password) >= 5 and len(password) <= 50 and
        set(password) <= allowed_password_characters)
def is_question_text_valid(text):
    return len(text) >= 10 and len(text) <= 2000
def is_question_title_valid(text):
    return len(text) >= 10 and len(text) <= 100
def is_answer_text_valid(text):
    return len(text) >= 10 and len(text) <= 2000
def is_comment_text_valid(text):
    return len(text) >= 10 and len(text) <= 280

@app.route("/register", methods=['POST', 'GET'])
def register():
    if 'username' in session:
        return redirect(url_for('main'))
    
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not is_username_valid(username):
            error = 'Логин пользователя может содержать только латинские буквы, цифры и символы ".", "-", "_", в количестве от 4 до 20.'
            return render_template('register.html', error=error, logged_in=False)
        if not is_password_valid(password):
            error = 'Пароль может содержать только латинские и кириллические буквы, цифры и символы из списка "!@#$;%^:&?*()_-+=\'"", в количестве от 5 до 50.'
            return render_template('register.html', error=error, logged_in=False)
        
        with get_db().session() as db:
            result = db.run(
                r'MATCH (n:User {username:$username}) RETURN n',
                username=username
                ).single()
            if result is not None:
                error = 'Этот логин уже занят, пожалуйста, выберите другой!'
                return render_template('register.html', error=error, logged_in=False)
            pass_hash = base64.b64encode(bcrypt.hashpw(
                password.encode('utf-8'), bcrypt.gensalt()
                )).decode('ascii')
            register_date = DateTime.now()
            db.run(
                r'CREATE (n:User {username:$username, pass_hash:$pass_hash, register_date:$register_date, rating: 0})',
                username=username, pass_hash=pass_hash, register_date=register_date
            )
            return redirect(url_for('main'))
    
    return render_template('register.html', error=error, logged_in=False)

@app.route("/login", methods=['POST', 'GET'])
def login():
    if 'username' in session:
        return redirect(url_for('main'))

    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if not is_username_valid(username):
            error = 'Логин пользователя может содержать только латинские буквы, цифры и символы ".", "-", "_", в количестве от 4 до 20.'
            return render_template('login.html', error=error, logged_in=False)
        if not is_password_valid(password):
            error = 'Пароль может содержать только латинские и кириллические буквы, цифры и символы из списка "!@#$;%^:&?*()_-+=\'"", в количестве от 5 до 50.'
            return render_template('login.html', error=error, logged_in=False)
        
        with get_db().session() as db:
            result = db.run(
                r'MATCH (n:User {username:$username}) RETURN n',
                username=username
                ).single()
            if result is None:
                error = 'Пользователя с таким логином не существует!'
                return render_template('login.html', error=error, logged_in=False)
            pass_hash = base64.b64decode(result['n']['pass_hash'])
            if bcrypt.hashpw(password.encode('utf-8'), pass_hash) == pass_hash:
                session['username'] = username
                return redirect(url_for('main'))
            else:
                error = 'Неверный пароль!'
                return render_template('login.html', error=error, logged_in=False)
    
    return render_template('login.html', error=error, logged_in=False)

@app.route("/logout")
def logout():
    session.pop('username', None)
    return redirect(url_for('main'))

@app.route("/question", methods=['POST', 'GET'])
def question():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    error = None
    username = session['username']

    if request.method == 'POST':
        title = request.form['title']
        question = request.form['question']
        discipline = request.form['discipline']
        date = DateTime.now()

        if not is_question_title_valid(title):
            error = "Заголовок должен содержать не менее 10 и не более 100 символов."
        if not is_question_text_valid(question):
            error = "Текст вопроса должен содержать не менее 10 и не более 2000 символов."
        if discipline is None or discipline == "":
            error = "Выберите предмет и дисциплину."

        if error is None:
            with get_db().session() as db:
                while (True):
                    id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
                    result = db.run(
                    r'MATCH (Q:Question {id: $id}) RETURN Q',
                    id = id
                    ).single()
                    if result is None:
                        break
                db.run(
                    r'MATCH (U:User {username:$username}), (D:Discipline {name:$discipline}) CREATE (D)<-[:CORRESPONDS]-(Q:Question {title:$title, question:$question, id: $id, date: $date, rating: 0, views: 0, needs_update: false})<-[r:ASKED]-(U)',
                    title=title, question=question, username = username, id=id, date=date, discipline=discipline
                )
                return url_for('q', id=id)
   

    with get_db().session() as db:
        result = db.run(r'MATCH (s:Subject)-[:CONTAINS]->(d:Discipline) RETURN s, d')
        data = {}
        for r in result:
            if r['s']['name'] not in data:
                data[r['s']['name']] = []
            data[r['s']['name']].append(r['d']['name'])
    
    return render_template('question.html', data=data, error=error, logged_in=True, my_name=username)


@app.route("/q/<id>",methods=['POST', 'GET'])
def q(id):
    with get_db().session() as db:
        logged_in = 'username' in session

        errors = []

        if request.method == 'POST':
            if not logged_in:
                return redirect(url_for('q', id=id))
            
            username = session['username']
            date = DateTime.now()

            if 'q_id' in request.form:
                comment = request.form['comment']
                if is_comment_text_valid(comment):
                    db.run(
                        r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) CREATE (Q)<-[:TO]-(C:Comment {comment:$comment, date:$date}) <-[:COMMENTED]-(U)',
                        username = username, id=id, comment=comment, date=date
                    )
            elif 'a_id' in request.form:
                comment = request.form['comment']
                a_id = request.form['a_id']
                if is_comment_text_valid(comment):
                    db.run(
                        r'MATCH (U:User {username:$username}), (A:Answer) WHERE id(A) = $a_id CREATE (A)<-[:TO]-(C:Comment {comment:$comment, date:$date})<-[:COMMENTED]-(U)',
                        username = username, a_id=int(a_id), comment=comment, date=date
                    )
            else:
                answer = request.form['answer']
                if is_answer_text_valid(answer):
                    db.run(
                        r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) CREATE (Q)<-[:TO]-(A:Answer {answer:$answer, date:$date, rating: 0}) <-[:ANSWERED]-(U)',
                        username = username, id=id, answer=answer, date=date
                    )
            return redirect('q', id=id)

        username = session['username'] if 'username' in session else ''

        result = db.run(
        r'''
            MATCH (D:Discipline)<-[:CORRESPONDS]-(Q:Question {id: $id})<-[r:ASKED]-(U:User)
            WHERE NOT ()-[:HIDDEN]->(Q)
            OPTIONAL MATCH (u:User {username:$username})
            OPTIONAL MATCH (u)-[v:VOTED]->(Q)
            RETURN Q,U,D,v,u.rating as R''',id=id, username=username
        ).single()
        if result is None:
            abort(404)

        data = {
            'question' : {
                'id': id,
                'title': result['Q']['title'],
                'text': result['Q']['question'],
                'date': result['Q']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
                'rating': result['Q']['rating'],
                'current_vote': result['v']['vote'] if result['v'] is not None else 0,
                'author': {'name': result['U']['username'], 'rating': result['U']['rating']},
                'discipline': result['D']['name'],
                'comments': []
            }, 
            'answers': [],
            'me' : {'rating': result['R']}
        }

        result = db.run(
        r'''
        MATCH (Q:Question {id: $id})<-[:TO]-(C:Comment)<-[:COMMENTED]-(U:User)
        WHERE NOT ()-[:HIDDEN]->(C)
        RETURN C,U
        ORDER BY C.date''',id=id
        )
        for r in result:
            data['question']['comments'].append({
                'text': r['C']['comment'],
                'id': r['C'].id,
                'author': {'name': r['U']['username'], 'rating': r['U']['rating']}
            })

        result = db.run(
        r'''
        MATCH (Q:Question {id: $id})<-[:TO]-(A:Answer)<-[:ANSWERED]-(U:User)
        WHERE NOT ()-[:HIDDEN]->(A)
        OPTIONAL MATCH (:User {username:$username})-[v:VOTED]->(A) 
        RETURN A,U,[
            (CU:User)-[:COMMENTED]->(C:Comment)-[:TO]->(A) WHERE NOT ()-[:HIDDEN]->(C) | [C.date, CU.username, C.comment, id(C), CU.rating]] 
            AS comments,v''',id=id, username=username
        )
        for r in result:
            answer = {
                'id': r['A'].id,
                'text': r['A']['answer'],
                'date': r['A']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
                'author': {'name': r['U']['username'], 'rating': r['U']['rating']},
                'rating': r['A']['rating'],
                'current_vote': r['v']['vote'] if r['v'] is not None else 0,
                'comments': [{
                    'date': comment[0].to_native().strftime('%d.%m.%Y %H:%M'),
                    'author': {'name': comment[1], 'rating': comment[4]},
                    'text': comment[2],
                    'id': comment[3]
                } for comment in sorted(r['comments'])]
            }
            data['answers'].append(answer)

        if logged_in:
            db.run(r'''
                MATCH (Q:Question {id: $id}), (U:User {username:$username}) 
                MERGE (U)-[r:VIEWED]->(Q)
                ON CREATE
                SET Q.views = Q.views + 1, Q.needs_update = true''',
                id=id, username=username
            )

        return render_template('q.html', data=data, logged_in=logged_in, my_name=username, errors=errors)
        # return f'''<h1>{title}</h1>'''    
# HTML-собрать и на странице поста указать автора поста

@app.route("/votes",methods=['POST'])
def votes():
    @unit_of_work(timeout=5)
    def trans_func(tx, form, username):
        vote = int(form['vote'])
        if (vote not in [-1, 0, 1]): return
        if 'q_id' in form:
            q_id = form['q_id']
            result = tx.run(
                r'MATCH (U:User {username:$username})-[v:VOTED]->(Q:Question {id:$id}) RETURN v',
                username = username, id=q_id
            ).single()
            if result is None:
                old_vote = 0
            else:
                old_vote = result['v']['vote']
            tx.run(
                r'MATCH (U:User {username:$username})-[v1:VOTED]->(Q:Question {id:$id}) DELETE v1',
                username = username, id=q_id
            )
            if vote != 0:
                tx.run(
                    r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) CREATE (U)-[v2:VOTED {vote:$vote}]->(Q)',
                    username = username, id=q_id, vote=vote
                )
            tx.run(
                r'MATCH (Q:Question {id:$id})<-[:ASKED]-(U:User) SET Q.rating = Q.rating + $inc, U.rating = U.rating + $inc',
                username = username, id=q_id, inc=vote - old_vote
            )
        elif 'a_id' in form:
            a_id = form['a_id']
            result = tx.run(
                r'MATCH (U:User {username:$username})-[v:VOTED]->(A:Answer) WHERE id(A) = $a_id RETURN v',
                username = username, a_id=int(a_id)
            ).single()
            if result is None:
                old_vote = 0
            else:
                old_vote = result['v']['vote']
            tx.run(
                r'MATCH (U:User {username:$username})-[v1:VOTED]->(A:Answer) WHERE id(A) = $a_id DELETE v1',
                username = username, a_id=int(a_id)
            )
            if vote != 0:
                tx.run(
                    r'MATCH (U:User {username:$username}), (A:Answer) WHERE id(A) = $a_id CREATE (U)-[v2:VOTED {vote:$vote}]->(A)',
                    username = username, a_id=int(a_id), vote=vote
                )
            tx.run(
                r'MATCH (A:Answer)<-[:ANSWERED]-(U:User) WHERE id(A)=$a_id SET A.rating = A.rating + $inc, U.rating = U.rating + $inc',
                username = username, a_id=int(a_id), inc=vote - old_vote
            )
    
    with get_db().session() as db:
        logged_in = 'username' in session
        if logged_in:
            db.write_transaction(trans_func, request.form, session['username'])
    return ''

@app.route("/report",methods=['POST'])
def report():
    logged_in = 'username' in session
    if not logged_in: return ''
    username = session['username']

    with get_db().session() as db:
        if 'q_id' in request.form:
            q_id = request.form['q_id']
            db.run(
                r'MATCH (U:User {username:$username}), (Q:Question {id:$id}) MERGE (U)-[r:REPORTED]->(Q)',
                username = username, id=q_id
            )
        elif 'a_id' in request.form:
            a_id = request.form['a_id']
            db.run(
                r'MATCH (U:User {username:$username}), (A:Answer) WHERE id(A) = $id MERGE (U)-[r:REPORTED]->(A)',
                username = username, id=int(a_id)
            )
        elif 'c_id' in request.form:
            c_id = request.form['c_id']
            db.run(
                r'MATCH (U:User {username:$username}), (C:Comment) WHERE id(C) = $id MERGE (U)-[r:REPORTED]->(C)',
                username = username, id=int(c_id)
            )
    return ''

def is_moderator(username):
    with get_db().session() as db:
        result = db.run(r'MATCH (u:User:Moderator {username:$username}) RETURN u', username=username).single()
        return result is not None

@app.route("/reported")
def reported():
    logged_in = 'username' in session
    if not logged_in: return redirect(url_for('main'))
    username = session['username']
    if not is_moderator(username): return redirect(url_for('main'))

    with get_db().session() as db:
        questions = []
        result = db.run(r'''
            MATCH (:User)-[:REPORTED]->(q:Question)
            WITH DISTINCT q
            MATCH (d:Discipline)<-[:CORRESPONDS]-(q)<-[:ASKED]-(a:User)
            RETURN d, a, q

            UNION

            MATCH (d:Discipline)<-[:CORRESPONDS]-(q:Question)<-[:ASKED]-(a:User)
            WHERE q.rating < -10
            RETURN d, a, q''')
        questions = [{
            'id': r['q']['id'],
            'title': r['q']['title'],
            'text': r['q']['question'],
            'date': r['q']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
            'rating': r['q']['rating'],
            'author': {'name': r['a']['username'], 'rating': r['a']['rating']},
            'discipline': r['d']['name']
        } for r in result]

        result = db.run(r'''
            MATCH (:User)-[:REPORTED]->(a:Answer)
            WITH DISTINCT a
            MATCH (a)<-[:ANSWERED]-(u:User)
            RETURN u, a
            
            UNION
            
            MATCH (a:Answer)<-[:ANSWERED]-(u:User)
            WHERE a.rating < -10
            RETURN u, a''')
        answers = [{
            'id': r['a'].id,
            'text': r['a']['answer'],
            'date': r['a']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
            'author': {'name': r['u']['username'], 'rating': r['u']['rating']},
            'rating': r['a']['rating']
        } for r in result]
        
        result = db.run(r'''
            MATCH (:User)-[:REPORTED]->(c:Comment)
            WITH DISTINCT c
            MATCH (c)<-[:COMMENTED]-(u:User)
            RETURN u, c''')
        comments = [{
            'date': r['c']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
            'author': {'name': r['u']['username'], 'rating': r['u']['rating']},
            'text': r['c']['comment'],
            'id': r['c'].id
        } for r in result]
        

        data = {
            'questions': questions,
            'answers': answers,
            'comments': comments
        }
    return render_template('reported.html', data=data, logged_in=True, my_name=username)

@app.route("/search")
def search():
    search_text = request.args.get('s', '')
    form_text = f'''
    <form method="get">
        <input type="text" id="s" name="s" value="{search_text}">
        <input type="submit" value="Find">
    </form>
    '''
    if search_text == '':
        return form_text
    
    text = '<h2>Search results</h2>'

    with get_db().session() as db:
        result = db.run(
            'CALL db.index.fulltext.queryNodes("titlesAndTexts", $text) YIELD node, score WHERE NOT ()-[:HIDDEN]->(node) RETURN node, score LIMIT 50', text=search_text
        )

        result_texts = []
        for r in result:
            url = url_for('q', id=r['node']['id'])
            title = r['node']['title']
            question = r['node']['question']
            if len(question) > 30:
                question = question[:30] + '...'

            result_texts.append(f'''
                <li><b><a href={url}>{title}</a></b><br>
                {question}
                </li>
            ''')
        if len(result_texts) == 0:
            text += '<p>Nothing was found</p>'
        else:
            text += '<ul>' + ''.join(result_texts) + '</ul>'
        return form_text + text

@app.route("/hide",methods=['POST'])
def hide():
    logged_in = 'username' in session
    if not logged_in: return ''
    username = session['username']
    if not is_moderator(username): return ''

    date = DateTime.now() + timedelta(days=30)

    with get_db().session() as db:
        if 'q_id' in request.form:
            q_id = request.form['q_id']
            db.run(
                r'''
                MATCH (U:User:Moderator {username:$username}), (Q:Question {id:$id})
                OPTIONAL MATCH ()-[rep:REPORTED]->(Q)
                MERGE (U)-[r:HIDDEN]->(Q)
                SET r.deletion_date=$date
                DELETE rep''',
                username = username, id=q_id, date=date
            )
        elif 'a_id' in request.form:
            a_id = request.form['a_id']
            db.run(
                r'''
                MATCH (U:User:Moderator {username:$username}), (A:Answer) 
                WHERE id(A) = $id
                OPTIONAL MATCH ()-[rep:REPORTED]->(A)
                MERGE (U)-[r:HIDDEN]->(A) 
                SET r.deletion_date=$date
                DELETE rep''',
                username = username, id=int(a_id), date=date
            )
        elif 'c_id' in request.form:
            c_id = request.form['c_id']
            db.run(
                r'''
                MATCH (U:User:Moderator {username:$username}), (C:Comment) 
                WHERE id(C) = $id
                OPTIONAL MATCH ()-[rep:REPORTED]->(C)
                MERGE (U)-[r:HIDDEN]->(C)
                SET r.deletion_date=$date
                DELETE rep''',
                username = username, id=int(c_id), date=date
            )
    return ''

@app.route("/hidden")
def hidden():
    logged_in = 'username' in session
    if not logged_in: return redirect(url_for('main'))
    username = session['username']
    if not is_moderator(username): return redirect(url_for('main'))

    with get_db().session() as db:
        questions = []
        result = db.run(r'''
            MATCH (:User)-[:HIDDEN]->(q:Question)
            MATCH (d:Discipline)<-[:CORRESPONDS]-(q)<-[:ASKED]-(a:User)
            RETURN d, a, q''')
        questions = [{
            'id': r['q']['id'],
            'title': r['q']['title'],
            'text': r['q']['question'],
            'date': r['q']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
            'rating': r['q']['rating'],
            'author': {'name': r['a']['username'], 'rating': r['a']['rating']},
            'discipline': r['d']['name']
        } for r in result]

        result = db.run(r'''
            MATCH (:User)-[:HIDDEN]->(a:Answer)
            MATCH (a)<-[:ANSWERED]-(u:User)
            RETURN u, a''')
        answers = [{
            'id': r['a'].id,
            'text': r['a']['answer'],
            'date': r['a']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
            'author': {'name': r['u']['username'], 'rating': r['u']['rating']},
            'rating': r['a']['rating']
        } for r in result]
        
        result = db.run(r'''
            MATCH (:User)-[:HIDDEN]->(c:Comment)
            MATCH (c)<-[:COMMENTED]-(u:User)
            RETURN u, c''')
        comments = [{
            'date': r['c']['date'].to_native().strftime('%d.%m.%Y %H:%M'),
            'author': {'name': r['u']['username'], 'rating': r['u']['rating']},
            'text': r['c']['comment'],
            'id': r['c'].id
        } for r in result]
        

        data = {
            'questions': questions,
            'answers': answers,
            'comments': comments
        }
    return render_template('hidden.html', data=data, logged_in=True, my_name=username)

@app.route("/unhide",methods=['POST'])
def unhide():
    logged_in = 'username' in session
    if not logged_in: return ''
    username = session['username']
    if not is_moderator(username): return ''

    with get_db().session() as db:
        if 'q_id' in request.form:
            q_id = request.form['q_id']
            db.run(
                r'MATCH (U:User:Moderator)-[r:HIDDEN]->(Q:Question {id:$id}) DELETE r', id=q_id
            )
        elif 'a_id' in request.form:
            a_id = request.form['a_id']
            db.run(
                r'''
                MATCH (U:User:Moderator)-[r:HIDDEN]->(A:Answer) 
                WHERE id(A) = $id
                DELETE r''', id=int(a_id)
            )
        elif 'c_id' in request.form:
            c_id = request.form['c_id']
            db.run(
                r'''
                MATCH (U:User:Moderator)-[r:HIDDEN]->(C:Comment) 
                WHERE id(C) = $id
                DELETE r''', id=int(c_id)
            )
    return ''

@app.route("/unreport",methods=['POST'])
def unreport():
    logged_in = 'username' in session
    if not logged_in: return ''
    username = session['username']
    if not is_moderator(username): return ''

    with get_db().session() as db:
        if 'q_id' in request.form:
            q_id = request.form['q_id']
            db.run(
                r'MATCH (U:User)-[r:REPORTED]->(Q:Question {id:$id}) DELETE r', id=q_id
            )
        elif 'a_id' in request.form:
            a_id = request.form['a_id']
            db.run(
                r'''
                MATCH (U:User)-[r:REPORTED]->(A:Answer) 
                WHERE id(A) = $id
                DELETE r''', id=int(a_id)
            )
        elif 'c_id' in request.form:
            c_id = request.form['c_id']
            db.run(
                r'''
                MATCH (U:User)-[r:REPORTED]->(C:Comment) 
                WHERE id(C) = $id
                DELETE r''', id=int(c_id)
            )
    return ''