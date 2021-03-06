from flask import render_template, request, session, redirect, flash
from webapp import app
from sqlalchemy import create_engine
from sqlalchemy_utils import database_exists, create_database
import psycopg2
import model
import pandas as pd
import numpy as np
from webapp.settings import APP_STATIC
import os
import getpass
import datetime

# The number of images to show
N = 36
# Initialize variables for connecting to database
user = getpass.getuser()
pswd = '1234'
host = 'localhost'
dbname = 'art_3'
db = None
con = None
# Establish a connection with the PSQL database
db = create_engine('postgres://{:s}:{:s}@{:s}/{:s}'.\
    format(user, pswd, host, dbname))
# Connect to database
con = psycopg2.connect(database=dbname, user=user, host=host, password=pswd)
# Define the number of rows in database
N_rows = 14852
if N_rows == None:
    # If number of rows is not known a priori, calculate from database
    qry = pd.read_sql_query('SELECT count(*) AS exact_count FROM artworks', con)
    N_rows = qry.values[0][0]
# Load the features-only pandas data frame in static folder
df_feat = pd.read_pickle(os.path.join(APP_STATIC, \
    'art_yr_label_cln2_cats_labs_sparse_cln_featuresonly.pickle'))
# Load the pandas dataframe with precomputed distance^2 term
df_feat_sqd = pd.read_pickle(os.path.join(APP_STATIC, \
    'art_yr_label_cln2_cats_labs_sparse_cln_featuresonly_distance2.pickle'))


@app.route('/')
@app.route('/index')
def index():
    """The main page - get images from k-means and show them to user"""
    # Get random initial values from k-means clusters
    rand_inds = model.two_inds_per_cluster(con)
    # Get a list of url strings (img) and store the index in the session var
    # Store each random image index as a value in the sessions dictionary
    # Note that indices are stored as strings
    img, session = append_random_imgs(rand_inds, con)
    # Send to template page
    return render_template('index.html', img=img, error=None)


@app.route('/demo_seed')
def demo_seed():
    """Like index page, but with predefined images for presenting as demo"""
    inds = [6352, 5121, 7332, 11110, 10679, 9802, 3105, 8820, 117, 12730, 6014,
            1643, 433, 4040, 5050, 2121, 7570, 12389, 3205, 7142, 898, 3190,
            395, 9023, 12162, 2502, 1350, 2276, 10198, 14156, 493, 13936, 6992,
            774, 7422, 4412]
    img, session = append_random_imgs(inds, con)
    return render_template('index.html', img=img)


@app.route('/results', methods=['POST'])
def results():
    """Takes in user choices, calculates user profile and returns similar art"""
    # Initialize variables
    rand_inds = N*[None]
    good_inds = []
    bad_inds = []
    # Get the initial choice from the sessions variable
    for i in range(N):
        rand_inds[i] = int(session.get('rnd_ind' + str(i), None))
    # Get the user's choices with  "getlist"  b/c form returns multiple values
    qlist = request.form.getlist('q')
    # Convert to list of ints (from list of strings)
    qlist = [int(q) for q in qlist]
    # Loop over all sample images and check which the user selected
    for i in range(N):
        if i in qlist:
            # Yes - user selected
            good_inds.append(rand_inds[i])
        else:
            # No - user did not select
            bad_inds.append(rand_inds[i])
    # Some checks on usage behavior - if fail, return to index.html with error
    if (len(good_inds) == 0 or len(good_inds) == len(rand_inds)):
        if len(good_inds) == 0:
            error = 'Please choose at least one artwork'
        if len(good_inds) == len(rand_inds):
            error = "Please don't choose all of the artworks"
        img, _ = append_random_imgs(rand_inds, con)
        return render_template('index.html', img=img, error=error)
    # RUN THE MODEL! #
    best_inds, top_features = model.get_similar_art(good_inds, bad_inds, df_feat, df_feat_sqd)
    # Write output to database
    USERDB = create_user_df(rand_inds, good_inds, bad_inds, best_inds)
    write_user_db(USERDF)
    # Get urls for best results
    imgout, glink, hreslink, alink, artwork_name = model.get_artwork_info(best_inds, con)
    return render_template("out.html", imgout=imgout, glink=glink, alink=alink,
                           hreslink=hreslink, artwork_name=artwork_name,
                           top_features=top_features)

@app.route('/about')
def about():
    """Returns about page with slides"""
    return render_template('about.html')

@app.route('/contact')
def contact():
    """Returns page with my contact info"""
    return render_template('contact.html')

@app.route('/unhappy')
def unhappy():
    """Tells user that their unhappiness with results has been recorded in db"""
    # Record that user is unhappy in the database
    write_user_db(USERDF, unhappy=1)
    return render_template('unhappy.html')

def create_user_df(rand_inds, good_inds, bad_inds, best_inds):
    time = datetime.datetime.now()
    userdict = {'randinds': ','.join([str(foo) for foo in rand_inds]),
              'good_inds': ','.join([str(foo) for foo in good_inds]),
              'bad_inds': ','.join([str(foo) for foo in bad_inds]),
              'best_inds': ','.join([str(foo) for foo in best_inds]),
              'unhappy': 0,
              'time': time}
    global USERDF
    USERDF = pd.DataFrame(data=userdict, index=range(1))
    return USERDF

def write_user_db(USERDF, unhappy=0):
    USERDF['unhappy'].iloc[[0]] = unhappy
    db = create_engine('postgres://{:s}:{:s}@{:s}/{:s}'.format(user, pswd,
                                                            host, 'artuser'))
    engine_user = create_engine('postgresql://' + user + ':1234@localhost/artuser')
    con = None
    con = psycopg2.connect(database='artuser', user=user, host=host, password=pswd)
    USERDF.to_sql('artuser', engine_user, if_exists='append')


def append_random_imgs(rand_inds, con):
    """Given a list of index values and a database connection, return a list of
       url strings to the images and the updated session variable"""
    img = []
    sql_query_pre = "SELECT url_to_thumb FROM artworks WHERE index="
    for i, rand_ind in enumerate(rand_inds):
        # Set the session index value (could also use a GLOBAL variable here)
        session['rnd_ind' + str(i)] = str(rand_ind)
        # Call database to get urls of thumbnail images from index value
        sql_query = sql_query_pre + str(rand_ind) + ";"
        thumb_url_np = pd.read_sql_query(sql_query, con)
        # Add url string to list
        img.append(thumb_url_np.values[0][0])
    return img, session
