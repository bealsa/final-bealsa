import omdb_secret #file containing api key
import requests
from bs4 import BeautifulSoup
import json
import sqlite3

from flask import Flask, render_template, request
app = Flask(__name__)

# RETRIEVING AND CACHING MOVIE DATA
## Caching
CACHE_FILE_NAME = "cache.json"

def open_cache():
    try:
        cache_file = open(CACHE_FILE_NAME, 'r')
        cache_contents = cache_file.read()
        cache_dict = json.loads(cache_contents)
        cache_file.close()
    except:
        cache_dict = {}
    return cache_dict

def save_cache(cache_dict):
    fw = open(CACHE_FILE_NAME, "w")
    dumped_json_cache = json.dumps(cache_dict)
    fw.write(dumped_json_cache)
    fw.close()

def construct_unique_key(BASE_URL, params): #make a url as the cache key
    params_strings = []
    connector= "_"
    for k in params.keys():
        params_strings.append(f'{k}_{params[k]}')
    params_strings.sort()
    unique_key = BASE_URL + connector + connector.join(params_strings)
    return unique_key

def make_request(baseurl, params={}):
    response = requests.get(baseurl, params)
    return response.text

def make_request_with_cache_omdb(baseurl, params={}):
    request_key = construct_unique_key(baseurl, params)
    if request_key in CACHE_DICT.keys():
        print("Using Cache")
        return CACHE_DICT[request_key]
    else:
        print("Fetching")
        CACHE_DICT[request_key] = json.loads(make_request(baseurl, params))
        save_cache(CACHE_DICT)
        return CACHE_DICT[request_key]

def make_request_with_cache_imdb(baseurl, params={}):
    request_key = construct_unique_key(baseurl, params)
    if request_key in CACHE_DICT.keys():
        print("Using Cache")
        return CACHE_DICT[request_key]
    else:
        print("Fetching")
        CACHE_DICT[request_key] = make_request(baseurl, params)
        save_cache(CACHE_DICT)
        return CACHE_DICT[request_key]


#make a separate make_request with cache for json/html

CACHE_DICT = open_cache()

## OMDb api information retrieval
'''Six fields to retrieve:
1. Title
2. Year
3. Rated
4. Genre
5. Plot
6. IMDb ID
'''

class OMDb:
    '''Information from OMDb site.

    Instance Attributes
    -------------------
    title: string
        movie/tv show title

    year: string
        movie/tv year(s)

    rated: string
        viewer rating for movie/tv show (PG/R)

    genre: string
        movie/tv show genre(s)

    plot: string
        description of the movie.tv show's plot
    '''
    def __init__(self, title, year, rated, genre, plot, imdb_id):
        self.title = title
        self.year = year
        self.rated = rated
        self. genre = genre
        self.plot = plot
        self.imdb_id = imdb_id

    def info(self):
        return self.title + " (" + self.year +")" + " (" + self.genre +")" + " ["+self.rated+"] " + ": " + self.plot


def get_omdb_instance(baseurl, params):
    '''Create an instance from a movie/tv show search.

    Parameters
    ----------
    search: string
        movie tv/show title

    Returns
    -------
    an OMDb instance
    '''
    response = make_request_with_cache_omdb(baseurl, params)
    try:
        title = response['Title']
    except:
        title = "No title"
    try:
        year = response['Year']
    except:
        year = "No Year"
    try:
        rated = response['Rated']
    except:
        rated = "NR"
    try:
        genre = response['Genre']
    except:
        genre = "No Genre"
    try:
        plot = response['Plot']
    except:
        plot = "No Plot"
    try:
        imdb_id =response['imdbID']
    except:
        imdb_id = "No ID"
    omdb_instance = OMDb(title, year, rated, genre, plot, imdb_id)

    return  omdb_instance


## IMDb website scraping
'''Five fields to retrieve:
1. Director/creator
2. Rating
3. Cast
4. User reviews
5. Trivia
'''

class IMDb:
    '''Information from IMDb site.

    Instance Attributes
    -------------------
    director: string
        director of movies/tv show

    rating: string
        numeric rating of movie/tv show from website

    cast: list
        cast members of movie/tv show

    reviews: string
        a user review of movie/tv show

    trivia: list
        a list of 5 trivia facts of movie/tv show
    '''
    def __init__(self, director, rating, cast, reviews, trivia):
        self.director = director
        self.rating = rating
        self.cast = cast
        self.reviews = reviews
        self.trivia = trivia

    # def info():
    #   pass

def get_imdb_instance(IMDb_ID):
    '''Create an instance from an IMDb ID.

    Parameters
    ----------
    IMDB ID: string
        ID retrieved from OMDb record.

    Returns
    -------
    an IMDb instance

    '''
    baseurl = 'https://www.imdb.com/title/'+IMDb_ID+'/'
    response = make_request_with_cache_imdb(baseurl)
    soup = BeautifulSoup(response, 'html.parser')

    try:
        director = soup.find('div', class_='credit_summary_item').find('a').text
    except:
        director = "No Director/Creator"
    try:
        rating =  soup.find('span', itemprop='ratingValue').text
    except:
        rating = "No Rating"
    try:
        all_cast = soup.find_all('td', class_=False)
        cast = []
        for actor in all_cast:
            try:
                star = actor.find('a').text.strip('\n').strip()
                cast.append(star)
            except:
                pass
    except:
        cast = "No Cast"
    try:
        reviews = soup.find('div', class_='user-comments').find('p', class_=False).text
    except:
        reviews = "No Reviews"
    try:
        baseurl = 'https://www.imdb.com/title/'+IMDb_ID+'/trivia?ref_=tt_trv_trv'
        response2 = make_request_with_cache(baseurl)
        soup2 = BeautifulSoup(response2, 'html.parser')

        trivia = []
        number = 0
        for info in soup2.find_all('div', class_="sodatext"):
            if number < 5:
                fact = info.text.strip('/n').strip()
                trivia.append(fact)
                number+=1
            else:
                pass
    except:
        trivia = "No Trivia"

    imdb_instance = IMDb(director, rating, cast, reviews, trivia)
    return imdb_instance

def print_trivia(imdb_instance):
    '''
    '''
    for i in range(len(imdb_instance.trivia)):
        print(f"[{i+1}] {imdb_instance.trivia[i]}")

def return_director(imdb_instance):
    director = imdb_instance.director.split()
    return director

# SAVING INFORMATION IN A DATABASE
'''GOAL IS TO TAKE A JSON AND STORE WITHIN A SQL FILE USING SQL LITE'''
DB_NAME = 'movie_director.sqlite'


def get_directors():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    result = cur.execute("Select * From Director").fetchall()
    conn.commit()
    conn.close()
    # [ID, fname, lname]
    #director_dict = get_directors()
    dict = {}
    for director in result:
        if (director[1] + " " + director[2]) not in dict.keys():
            dict[director[1] + " " + director[2]] = director[0]
    return dict

director_dict = get_directors()

def create_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    drop_director = '''
        DROP TABLE IF EXISTS "Director"
    '''
    create_director = '''
        CREATE TABLE IF NOT EXISTS "Director" (
            "Id"  INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "LastName"  TEXT NOT NULL,
            "FirstName" TEXT NOT NULL
        )
    '''
    drop_movie = '''
        DROP TABLE IF EXISTS "Movie"
    '''
    create_movie = '''
        CREATE TABLE IF NOT EXISTS "Movie" (
            'Id' INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            'Title' TEXT NOT NULL,
            'Year' INTEGER NOT NULL,
            'Rating' INTEGER,
            'DirectorId' INTEGER
        )
    '''
    cur.execute(drop_director)
    cur.execute(drop_movie)
    cur.execute(create_director)
    cur.execute(create_movie)
    conn.commit()
    conn.close()

def load_director():

    insert_director = '''
    INSERT INTO Director
    VALUES (NULL, ?, ?)
    '''

    f = open('cache.json')
    cache_data = json.load(f)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    for url, results in cache_data.items():
        if 'omdb' in url:
            try:
                director_split = (results)["Director"].split()
                cur.execute(insert_director,
                [ director_split[0], director_split[1] ]
                )
            except KeyError:
                pass
    conn.commit()
    conn.close()


def load_movie():
    insert_movie = '''
    INSERT INTO Movie
    VALUES (NULL, ?, ?, ?, ?)
    '''
    #(Select D.Id From Director as D where D.FirstName = ? and D.LastName = ?)
    f = open('cache.json')
    cache_data = json.load(f)

    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    #director_dict = get_directors()
    for url, results in cache_data.items():
        if 'omdb' in url:
            try:
                cur.execute(insert_movie,
                [ (results)["Title"], (results)["Year"], results["imdbRating"], director_dict[results["Director"]]])
                #(results)["Director"].split()[0], (results)["Director"].split()[1]]
                print(results['Director'])
            except KeyError:
                pass
    conn.commit()
    conn.close()

#Flask
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/handle_form', methods=['POST', 'GET'])
def handle_the_form():
    search = request.form["movie"]
    baseurl = 'http://www.omdbapi.com/?'
    params = {"apikey": omdb_secret.API_KEY, "t": search}

    return baseurl, params


if __name__ == '__main__':
    app.run(debug=True)
    baseurl = 'http://www.omdbapi.com/?'
    params = {"apikey": omdb_secret.API_KEY, "t": "frozen"}
    print(((get_imdb_instance(get_omdb_instance(baseurl, params).imdb_id))))


    create_db()
    load_director()
    load_movie()


