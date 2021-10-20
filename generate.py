from neo4j import GraphDatabase
from neo4j.time import DateTime
import bcrypt, base64
import os, random, string

neo4j_pass = os.environ.get('NEO4J_PASS')
neo4j_uri = 'neo4j+s://1f59f68c.databases.neo4j.io'
get_db = GraphDatabase.driver(neo4j_uri, auth=('neo4j', neo4j_pass))

def add_user(username, password):
    print(username)
    with get_db.session() as db:
        pass_hash = base64.b64encode(bcrypt.hashpw(
                password.encode('utf-8'), bcrypt.gensalt()
                )).decode('ascii')
        date = DateTime.now()
        db.run(
            r'CREATE (n:User {username:$username, pass_hash:$pass_hash, register_date:$register_date})',
            username=username, pass_hash=pass_hash, register_date=date
        )

l = []

def add_question(title, question):
    with get_db.session() as db:
        id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        print(id)
        date = DateTime.now()
        db.run(
            r'CREATE (Q:Question {title:$title, question:$question, id: $id, date: $date, votes: 0})',
            title=title, question=question, id=id, date=date
        )
        l.append(id)

def add_author(id, author):
    print(author)
    with get_db.session() as db:
        db.run(
            r'MATCH (Q:Question {id: $id}), (U:User {username: $username}) CREATE (U)-[:ASKED]->(Q)',
            id=id, username=author
        )
def add_view(id, user):
    print(user, id)
    with get_db.session() as db:
        db.run(
            r'MATCH (Q:Question {id: $id}), (U:User {username: $username}) CREATE (U)-[:VIEWED]->(Q)',
            id=id, username=user
        )

titles = [
    'Углеводы',
    'Соли',
    'Реакция сырья с растворами',
    'Смена конформаций ',
    'Строение молекулы',
    'Строение атома',
    'Beta-распад',
    'Дефект масс',
    'Импульс фотона',
    'Вычисление кинетической энергии',
    'Окончания падежей',
    'Падежи при времени действия',
    'Фонемы северных говоров',
    'Определение вывода из взаимосвязанных понятий и суждений',
    'Аффрикаты',
    'Что такое логическое умножение',
    'Отображение А: R2 → R2 для выражения',
    'Свойство характеристического уравнения',
    'Задача на определение вероятности',
    'Определение несовместных событий'
]

questions = [
    'Вопрос: Какие группы углеводов относятся к моносахаридам',
    'К каким солям относятся такие химические соединения как CuOH, NaOH, Al(OH)3',
    'Положительную реакцию с раствором железоаммониевых квасцов дают какие виды сырья?',
    'Быстрая смена конформаций в молекуле циклопентана называется...?',
    'Какое строение имеет оксид натрия?',
    'В ядре атома натрия 23 частицы, из них 12 нейтронов. Сколько в ядре протонов? Сколько электронов в нейтральном атоме?',
    'При β – распаде новый элемент занял место в таблице Менделеева',
    'Что такое дефект масс? И В каком случае ни массовое, ни зарядовое число ядра не изменяется? 1) При альфа-распаде 2) При бета- распаде 3)При испускании гамма-кванта 4) При испускании нейтрона 5) При испускании позитрона',
    'Чему равен импульс фотона (кг•м/с), испущенного атомом при переходе электрона из одного состояния в другое, отличающееся по энергии на 4,8•10-19Дж?',
    'Максимальное значение кинетической энергии свободно колеблющегося на пружине груза равно 5 Дж, максимальное значение его потенциальной энергии 5 Дж. В каких пределах изменяется полная механическая энергия груза?',
    'Окончания именительного и винительного падежей среднего рода множественного числа — это?',
    'Какие  могут употребляться падежи в латинском языке для обозначении времени действия?',
    'В каких условиях в ударном слоге фонема < а > реализуется в [е] в северных говорах',
    'Вывод из взаимосвязанных понятий и суждений, относящихся к некоторой предметной области, - это',
    'Одинаковое ли количество аффрикат функционирует в русских говорах',
    'Логическое умножение-этоА) конъюнкция Б) дизъюнкция В) импликация Г) эквиваленция',
    'Отображение А: R2 → R2, заданное выражением Ах = (хсos a, ysin a), где а — некоторый фиксированный угол, является?',
    'Если характеристическое уравнение квадратной матрицы порядка n имеет n попарно различных действительных корней, то эта матрица подобна некоторой матрице',
    'Из 500 деталей на складе 10 оказались бракованными. Какова вероятность взять исправную деталь?',
    'События называют несовместными, если...?'
]

ids = ['6isljv0s4j', 'wa0gje89lm', 'bwny97hv2g', 'dop19lwu45', 'uoeu6bfuq1', '6kwsoofe8z', 'x5vw9k6s09', 'ukhvbth5ol', 'g475l2s8fv', '3gsxyrrbb7', 'atgdxbc44u', 'cdn87w31ra', '5rmetouwui', 'b8noflbiz2', '753rprhbt6', 'stne3h4m22', 'pzy6tb40w4', 'jf6zzejice', 'v0wpdurlv6', '0bg0lu0qv4']

topics = [
    0, 0, 1, 0, 2,
    0, 1, 1, 0, 2,
    0, 0, 1, 2, 1,
    0, 1, 1, 2, 2
]

for i in range(50):
    username = 'user' + str(i+1)
    if i < 20:
        subjects = [i // 5, random.randrange(0, 4)]
        while subjects[1] == subjects[0]:
            subjects[1] = random.randrange(0, 4)
        fav_topic = topics[i]
    else:
        subjects = [random.randrange(0, 4), random.randrange(0, 4)]
        while subjects[1] == subjects[0]:
            subjects[1] = random.randrange(0, 4)
        fav_topic = random.randrange(0, 3)

    for sub_i in range(2):
        subject = subjects[sub_i]
        for j in range(5):
            index = subject * 5 + j
            if sub_i == 0 and topics[index] == fav_topic:
                add_view(ids[index], username)
            elif random.randrange(0, 5) == 0:
                add_view(ids[index], username)
    #last_id = random.randrange(0, 20)
    #while last_id // 5 in subjects:
    #    last_id = random.randrange(0, 20)
    #add_view(ids[last_id], username)
