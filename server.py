#!/bin/env  python3
from __future__ import print_function

import hashlib
import json
import os
import random
import re
import shutil
import string
import tempfile
from os import listdir

import bcrypt
import nltk
# import numpy as np # Removed
import pandas as pd
import pytz
from flask import (Flask, Response, flash, jsonify, redirect, render_template,
                   request, session, url_for)
from flask_sqlalchemy import SQLAlchemy

from dotenv import load_dotenv
load_dotenv()
import os
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# nltk.download('punkt') # we should prefetch
# import pickle # Removed
from collections import Counter
from datetime import datetime

# Gemini API related imports
from google import genai

# Removed TensorFlow and Keras related imports
# import tensorflow
# import tensorflow.keras
# from nltk.corpus import stopwords # Removed
# from nltk.stem.porter import PorterStemmer # Removed
# from tensorflow.keras import backend as K # Removed
# from tensorflow.keras import metrics, optimizers # Removed
# from tensorflow.keras.layers import * # Removed (Dense, Embedding, Flatten, Conv1D, MaxPooling1D)
# from tensorflow.keras.models import Model, Sequential # Removed
# from tensorflow.keras.preprocessing.sequence import pad_sequences # Removed
# from tensorflow.keras.preprocessing.text import Tokenizer # Removed
import re
import ast
from more_functions import *
from nltk.tokenize import sent_tokenize
from more_functions import getabstracts, undic, gene_category

GENECUP_PROMPT_TEMPLATE = ""
try:
    with open("genecup_synthesis_prompt.txt", "r") as f:
        GENECUP_PROMPT_TEMPLATE = f.read()
except FileNotFoundError:
    print("Warning: genecup_synthesis_prompt.txt not found.  LLM prompts will be incomplete.")
except Exception as e:
    print(f"Error loading genecup_synthesis_prompt.txt: {e}. LLM prompts will be affected.")

VERSION=None

def version():
    global VERSION
    if VERSION is None:
        with open("VERSION", 'r') as file:
            VERSION = file.read()
    return VERSION


app=Flask(__name__)
datadir=os.environ.get("GENECUP_DATADIR", "./")

app.config['SECRET_KEY'] = '#DtfrL98G5t1dC*4'
sqlitedb = 'sqlite:///'+datadir+'/userspub.sqlite'
print(sqlitedb)
app.config['SQLALCHEMY_DATABASE_URI'] = sqlitedb
db = SQLAlchemy(app)


def get_sentences_from_file(file_path, gene_name, category_name=None):
    """Reads a sentence file and returns sentences matching a gene and category."""
    matching_sentences = []
    try:
        with open(file_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    (gene, nouse, cat, pmid, text) = line.split("\t")
                    cat_match = (category_name is None) or (cat.strip().upper() == category_name.strip().upper())
                    if (gene.strip().upper() == gene_name.strip().upper() and cat_match):
                        matching_sentences.append({'pmid': pmid, 'text': text, 'category': cat})
                except ValueError:
                    continue
    except FileNotFoundError:
        print(f"Sentence file not found: {file_path}")
    except Exception as e:
        print(f"Error reading sentence file {file_path}: {e}")
    return matching_sentences


# nltk expects tokenizers at nltk_data/tokenizers/punkt
# nltk.data.path.append("./nlp/")

# Validate punkt tokenizer is available
try:
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print("ERROR: NLTK punkt_tab tokenizer not found. Set NLTK_DATA or install punkt_tab data.")
    print("  NLTK data paths: " + str(nltk.data.path))
    raise SystemExit(1)

# Initialize database within application context
with app.app_context():
    db.create_all()

# Configure Gemini API Client
# IMPORTANT: Set the GEMINI_API_KEY environment variable
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = None
if not GEMINI_API_KEY:
    print("Warning: GEMINI_API_KEY environment variable not set. Stress classification via Gemini will not work.")
else:
    try:
        gemini_client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print(f"Error initializing Gemini API client: {e}")
        GEMINI_API_KEY = None
'''
STRESS_PROMPT_TEMPLATE = ""
try:
    with open("stress_prompt.txt", "r") as f_prompt:
        STRESS_PROMPT_TEMPLATE = f_prompt.read()
except FileNotFoundError:
    print("FATAL ERROR: stress_prompt.txt not found. Stress classification will fail.")
except Exception as e:
    print(f"FATAL ERROR: Could not read stress_prompt.txt: {e}")

# few shot Function to classify stress using Gemini API
def classify_stress_with_gemini(sentence_text):
    if not GEMINI_API_KEY:
        print("Gemini API key not configured. Skipping classification.")
        return "error_no_api_key"

    # --- THIS IS THE MODIFIED PART ---
    # Check if the prompt template was loaded successfully
    if not STRESS_PROMPT_TEMPLATE:
        print("Stress prompt template is not available. Skipping classification.")
        return "error_no_prompt_template"

    try:
        # Call the API using the new Client
        prompt_text = STRESS_PROMPT_TEMPLATE + f'\nSentence: {sentence_text}\nClassification:'
        print(f"Gemini API call: few-shot stress classification (gemini-2.5-pro)\n  Prompt: {prompt_text}")
        response = gemini_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt_text
        )
        print(f"  Gemini response: {response.text.strip()}")
        # We need to parse the classification from the response
        classification = response.text.strip().lower()

        # The model might return "Cellular Level Stress" or "Organismal Stress"
        if "cellular" in classification:
            return "neg"  # 'neg' for Cellular Level Stress
        elif "organismal" in classification:
            return "pos"  # 'pos' for Organismal Stress
        else:
            print(f"Warning: Gemini returned unexpected classification: '{classification}' for sentence: '{sentence_text}'")
            return "unknown"

    except Exception as e:
        print(f"Error calling Gemini API for stress classification: {e}")
        return "error_api_call"


# zero-shot Function to classify stress using Gemini API
def classify_stress_with_gemini(sentence_text):
    if not GEMINI_API_KEY:
        print("Gemini API key not configured. Skipping classification.")
        return "error_no_api_key"

    try:
        prompt = f"""Classify the following sentence based on whether it describes 'systemic stress' or 'cellular stress'.
Please return ONLY the word 'systemic' if it describes systemic stress, or ONLY the word 'cellular' if it describes cellular stress. Do not add any other explanation or punctuation.

Sentence: "{sentence_text}"

Classification:"""

        print(f"Gemini API call: zero-shot stress classification (gemini-2.5-pro)\n  Prompt: {prompt}")
        response = gemini_client.models.generate_content(
            model='gemini-2.5-pro',
            contents=prompt
        )
        print(f"  Gemini response: {response.text.strip()}")
        classification = response.text.strip().lower()

        if classification == "systemic":
            return "pos"  # 'pos' for systemic stress
        elif classification == "cellular":
            return "neg"  # 'neg' for cellular stress
        else:
            print(f"Warning: Gemini returned unexpected classification: '{classification}' for sentence: '{sentence_text}'")
            return "unknown"

    except Exception as e:
        print(f"Error calling Gemini API for stress classification: {e}")
        return "error_api_call"
'''

# Sqlite database
class users(db.Model):
    __tablename__='user'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

# Preprocessing of words for CNN (REMOVED)
# def clean_doc(doc, vocab):
#     doc = doc.lower()
#     tokens = doc.split()
#     re_punc = re.compile('[%s]' % re.escape(string.punctuation))
#     tokens = [re_punc.sub('' , w) for w in tokens]
#     tokens = [word for word in tokens if len(word) > 1]
#     stop_words = set(stopwords.words('english'))
#     tokens = [w for w in tokens if not w in stop_words]
#     porter = PorterStemmer()
#     stemmed = [porter.stem(word) for word in tokens]
#     return tokens

# Load tokenizer (REMOVED)
# with open('./nlp/tokenizer.pickle', 'rb') as handle:
#     tokenizer = pickle.load(handle)

# Load vocabulary (REMOVED)
# with open('./nlp/vocabulary.txt', 'r') as vocab_file_handle: # Renamed variable to avoid conflict
#     vocab_text = vocab_file_handle.read() # Renamed variable

# def tf_auc_score(y_true, y_pred): (REMOVED)
#     return tensorflow.metrics.AUC()(y_true, y_pred)

# K.clear_session() (REMOVED)

# Create the CNN model (REMOVED)
# def create_model(vocab_size, max_length):
#     model = Sequential()
#     model.add(Embedding(vocab_size, 32, input_length=max_length))
#     model.add(Conv1D(filters=16, kernel_size=4, activation='relu'))
#     model.add(MaxPooling1D(pool_size=2))
#     model.add(Flatten())
#     model.add(Dense(10, activation='relu'))
#     model.add(Dense(1, activation='sigmoid'))
#     opt = tensorflow.keras.optimizers.Adamax(learning_rate=0.002, beta_1=0.9, beta_2=0.999)
#     model.compile(loss='binary_crossentropy', optimizer=opt, metrics=[tf_auc_score])
#     return model

# Use addiction ontology by default
import ast # Moved import ast here as it's first used here.
onto_cont=open("addiction.onto","r").read()
dictionary=ast.literal_eval(onto_cont)


@app.route("/")
def root():
    if 'email' in session:
        ontoarchive()
        onto_len_dir = session['onto_len_dir']
        onto_list = session['onto_list']
    else:
        onto_len_dir = 0
        onto_list = ''

    onto_cont=open("addiction.onto","r").read()
    dict_onto=ast.literal_eval(onto_cont)
    return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())


@app.route("/login", methods=["POST", "GET"])
def login():
    onto_len_dir = 0
    onto_list = ''
    onto_cont=open("addiction.onto","r").read()
    dict_onto=ast.literal_eval(onto_cont)
    email = None

    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        found_user = users.query.filter_by(email=email).first()
        if (found_user and (bcrypt.checkpw(password.encode('utf8'), found_user.password))):
            session['email'] = found_user.email
            #print(bcrypt.hashpw(session['email'].encode('utf8'), bcrypt.gensalt()))
            session['hashed_email'] = hashlib.md5(session['email'] .encode('utf-8')).hexdigest()
            session['name'] = found_user.name
            session['id'] = found_user.id
            flash("Login Succesful!")
            ontoarchive()
            onto_len_dir = session['onto_len_dir']
            onto_list = session['onto_list']
        else:
            flash("Invalid username or password!", "inval")
            return render_template('signup.html',version=version())
    return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())


@app.route("/signup", methods=["POST", "GET"])
def signup():
    onto_len_dir = 0
    onto_list = ''
    onto_cont=open("addiction.onto","r").read()
    dict_onto=ast.literal_eval(onto_cont)

    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        found_user = users.query.filter_by(email=email).first()

        if (found_user and (bcrypt.checkpw(password.encode('utf8'), found_user.password)==False)):
            flash("Already registered, but wrong password!", "inval")
            return render_template('signup.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())

        session['email'] = email
        session['hashed_email'] = hashlib.md5(session['email'] .encode('utf-8')).hexdigest()
        session['name'] = name
        password = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
        user = users(name=name, email=email, password = password)
        if found_user:
            session['email'] = found_user.email
            session['hashed_email'] = hashlib.md5(session['email'] .encode('utf-8')).hexdigest()
            session['id'] = found_user.id
            found_user.name = name
            db.session.commit()
            ontoarchive()
            onto_len_dir = session['onto_len_dir']
            onto_list = session['onto_list']
        else:
            db.session.add(user)
            db.session.commit()
            newuser = users.query.filter_by(email=session['email']).first()
            session['id'] = newuser.id
            os.makedirs(datadir+"/user/"+str(session['hashed_email']))
            session['user_folder'] = datadir+"/user/"+str(session['hashed_email'])
            os.makedirs(session['user_folder']+"/ontology/")

        flash("Login Succesful!")
        return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())
    else:
        if 'email' in session:
            flash("Already Logged In!")
            return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())
        return render_template('signup.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())


@app.route("/signin", methods=["POST", "GET"])
def signin():
    email = None
    if request.method == "POST":
        email = request.form['email']
        password = request.form['password']
        found_user = users.query.filter_by(email=email).first()

        if (found_user and (bcrypt.checkpw(password.encode('utf8'), found_user.password))):
            session['email'] = found_user.email
            session['hashed_email'] = hashlib.md5(session['email'].encode('utf-8')).hexdigest()
            session['name'] = found_user.name
            session['id'] = found_user.id
            flash("Login Succesful!")
            #onto_len_dir = 0
            #onto_list = ''
            onto_cont=open("addiction.onto","r").read()
            ontoarchive()
            onto_len_dir = session['onto_len_dir']
            onto_list = session['onto_list']
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())
        else:
            flash("Invalid username or password!", "inval")
            return render_template('signup.html',version=version())
    return render_template('signin.html',version=version())

# change password
@app.route("/<nm_passwd>", methods=["POST", "GET"])
def profile(nm_passwd):
    try:
        if "_" in str(nm_passwd):
            user_name = str(nm_passwd).split("_")[0]
            user_passwd = str(nm_passwd).split("_")[1]
            user_passwd = "b\'"+user_passwd+"\'"
            found_user = users.query.filter_by(name=user_name).first()

            if request.method == "POST":
                password = request.form['password']
                session['email'] = found_user.email
                session['hashed_email'] = hashlib.md5(session['email'] .encode('utf-8')).hexdigest()
                session['name'] = found_user.name
                session['id'] = found_user.id
                password = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt())
                found_user.password = password
                db.session.commit()
                flash("Your password is changed!", "inval")
                onto_len_dir = 0
                onto_list = ''
                onto_cont=open("addiction.onto","r").read()
                dict_onto=ast.literal_eval(onto_cont)
                return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())
            # remove reserved characters from the hashed passwords
            reserved = (";", "/", "?", ":", "@", "=", "&", ".")
            def replace_reserved(fullstring):
                for replace_str in reserved:
                    fullstring = fullstring.replace(replace_str,"")
                return fullstring
            replaced_passwd = replace_reserved(str(found_user.password))

            if replaced_passwd == user_passwd:
                return render_template("/passwd_change.html", name=user_name,version=version())
            else:
                return "This url does not exist"
        else:
            return "This url does not exist"
    except (AttributeError):
        return "This url does not exist"


@app.route("/logout")
def logout():
    onto_len_dir = 0
    onto_list = ''
    onto_cont=open("addiction.onto","r").read()
    dict_onto=ast.literal_eval(onto_cont)

    if 'email' in session:
        global user1
        if session['name'] != '':
            user1 = session['name']
        else:
            user1 = session['email']
    flash(f"You have been logged out, {user1}", "inval") # Used f-string for clarity
    session.pop('email', None)
    session.clear()
    return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())


@app.route("/about")
def about():
    return render_template('about.html',version=version())


# Ontology selection
@app.route("/index_ontology", methods=["POST", "GET"])
def index_ontology():
    namecat2 = request.args.get('onto')
    session['namecat']=namecat2

    if (namecat2 == 'addiction' or namecat2 == 'Select your ontology' ):
        session['namecat']='addiction'
        onto_cont=open("addiction.onto","r").read()
    else:
        dirlist = os.listdir(session['user_folder']+"/ontology/")
        for filename in dirlist:
            onto_name = filename.split('_0_')[1]
            if namecat2 == onto_name:
                onto_cont = open(session['user_folder']+"/ontology/"+filename+"/"+namecat2+".onto", "r").read()
                break
    dict_onto=ast.literal_eval(onto_cont)
    onto_len_dir = session['onto_len_dir']
    onto_list = session['onto_list']
    return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = session['namecat'], dict_onto=dict_onto ,version=version())


@app.route("/ontology", methods=["POST", "GET"])
def ontology():
    namecat2 = request.args.get('onto')
    select_date=request.args.get('selected_date')
    namecat_exist=0

    if select_date != None:
        time_extension = str(select_date)
        time_extension = time_extension.split('_0_')[0]
        namecat = str(select_date).split('_0_')[1]
        time_extension = time_extension.replace(':', '_')
        time_extension = time_extension.replace('-', '_')

        if ('email' in session):
            session['namecat'] = session['user_folder']+"/ontology/"+str(time_extension)+"_0_"+namecat+"/"+namecat
        else:
            session['namecat']=tempfile.gettempdir()+'/'+namecat
        onto_cont = open(session['namecat']+".onto","r").read()

        if onto_cont=='':
            dict_onto={}
        else:
            dict_onto=ast.literal_eval(onto_cont)
    elif (('email' in session) and (namecat2 == 'addiction')):
        namecat='addiction'
        session['namecat']=namecat
        onto_cont = open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
    else:
        if (('email' in session) and ((namecat2 != None) and (namecat2 != 'choose your ontology'))):
            namecat=namecat2
            dirlist = os.listdir(session['user_folder']+"/ontology/")

            for filename in dirlist:
                onto_name = filename.split('_0_')[1]
                if onto_name==namecat:
                    namecat_exist=1
                    namecat_filename=filename
                    break
            if namecat_exist==1:
                session['namecat'] = session['user_folder']+"/ontology/"+namecat_filename+'/'+namecat
            else:
                onto_cont = open("addiction.onto","r").read()
                dict_onto=ast.literal_eval(onto_cont)
        else:
            namecat='addiction'
            session['namecat']=namecat
            onto_cont = open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)

    if request.method == "POST":
        maincat = request.form['maincat']
        subcat = request.form['subcat']
        keycat = request.form['keycat']
        namecat = request.form['namecat']
        namecat_exist=0
        maincat=re.sub('[^,a-zA-Z0-9 \n]', '', maincat)
        subcat=re.sub('[^,a-zA-Z0-9 \n]', '', subcat)
        keycat=re.sub('[^,a-zA-Z0-9 \n]', '', keycat)
        keycat = keycat.replace(',', '|')
        keycat = re.sub("\s+", ' ', keycat)
        keycat = keycat.replace(' |', '|')
        keycat = keycat.replace('| ', '|')
        namecat=re.sub('[^,a-zA-Z0-9 \n]', '', namecat)

        # Generate a unique session ID depending on timestamp to track the results
        timestamp = datetime.utcnow().replace(microsecond=0)
        timestamp = timestamp.replace(tzinfo=pytz.utc)
        timestamp = timestamp.astimezone(pytz.timezone("America/Chicago"))
        timeextension = str(timestamp)
        timeextension = timeextension.replace(':', '_')
        timeextension = timeextension.replace('-', '_')
        timeextension = timeextension.replace(' ', '_')
        timeextension = timeextension.replace('_06_00', '')
        session['timeextension'] = timeextension

        if request.form['submit'] == 'add':  # Add new keywords or create a new ontology
            if ('email' in session):
                session['namecat']=namecat
                if (namecat=='addiction'):
                    flash("You cannot change addiction keywords but a new ontology will be saved as 'addictionnew', instead","inval")
                    namecat='addictionnew'
                    session['namecat']=namecat
                session['user_folder'] = datadir+"/user/"+str(session['hashed_email'])
                dirlist = os.listdir(session['user_folder']+"/ontology/")
                for filename in dirlist:
                    onto_name = filename.split('_0_')[1]
                    if onto_name==namecat:
                        namecat_exist=1  # Add new keywords
                        namecat_filename=filename
                        break
                if namecat_exist==0:  # Create a new ontology folder
                    os.makedirs(session['user_folder']+"/ontology/"+str(timeextension)+"_0_"+namecat,exist_ok=True)
                    session['namecat'] = session['user_folder']+"/ontology/"+str(timeextension)+"_0_"+namecat+"/"+namecat
                    if namecat=='addictionnew':
                        with open("addiction.onto","r") as f1:
                            with open(session['namecat']+".onto", "w") as f2:
                                for line in f1:
                                    f2.write(line)
                    else:
                        f= open(session['namecat']+".onto","w")
                        dict_onto={}
                else:
                    session['namecat'] = session['user_folder']+"/ontology/"+namecat_filename+'/'+namecat

                onto_cont=open(session['namecat']+".onto",'r').read()
                if onto_cont=='':
                    dict_onto={}
                else:
                    dict_onto=ast.literal_eval(onto_cont)

                flag_kw=0
                if (',' in maincat) or (',' in subcat):
                    flash("Only one word can be added to the category and subcategory at a time.","inval")
                elif maincat in dict_onto.keys():  # Layer 2, main category
                    if subcat in dict_onto[maincat].keys():  # Layer 3, keywords shown in results
                        keycat_ls = keycat.split('|')
                        for kw in str.split(next(iter(dict_onto[maincat][subcat])), '|'):  # Layer 4, synonyms
                            for keycat_word in keycat_ls:
                                if kw==keycat_word:
                                    flash("\""+kw+"\" is already in keywords under the subcategory \""+ subcat \
                                        + "\" that is under the category \""+ maincat+"\"","inval")
                                    flag_kw=1
                        if flag_kw==0:
                            dict_onto[maincat][subcat]= '{'+next(iter(dict_onto[maincat][subcat]))+'|'+keycat+'}'
                            dict_onto=str(dict_onto).replace('\'{','{\'')
                            dict_onto=str(dict_onto).replace('}\'','\'}')
                            dict_onto=str(dict_onto).replace('}},','}},\n')
                            with open(session['namecat']+'.onto', 'w') as file3:
                                file3.write(str(dict_onto))
                    else:
                        dict_onto[maincat][subcat]='{'+subcat+'|'+keycat+'}'
                        dict_onto=str(dict_onto).replace('\'{','{\'')
                        dict_onto=str(dict_onto).replace('}\'','\'}')
                        dict_onto=str(dict_onto).replace('}},','}},\n')
                        with open(session['namecat']+'.onto', 'w') as file3:
                            file3.write(str(dict_onto))
                else:
                    dict_onto[maincat]= '{'+subcat+'\': {\''+keycat+'}'+'}'
                    dict_onto=str(dict_onto).replace('\"{','{\'')
                    dict_onto=str(dict_onto).replace('}\"','\'}')
                    dict_onto=str(dict_onto).replace('\'{','{\'')
                    dict_onto=str(dict_onto).replace('}\'','\'}')
                    dict_onto=str(dict_onto).replace('}},','}},\n')
                    with open(session['namecat']+'.onto', 'w') as file3:
                        file3.write(str(dict_onto))
            else:
                if namecat=='addiction':
                    flash("You must login to change the addiction ontology.")
                else:
                    flash("You must login to create a new ontology.")

        if request.form['submit'] == 'remove':
            if ('email' in session):
                session['namecat']=namecat
                if (namecat=='addiction'):
                    flash("You cannot change addiction keywords but a new ontology will be saved as 'addictionnew', instead","inval")
                    namecat='addictionnew'
                    session['namecat']=namecat
                session['user_folder'] = datadir+"/user/"+str(session['hashed_email'])
                dirlist = os.listdir(session['user_folder']+"/ontology/")
                for filename in dirlist:
                    onto_name = filename.split('_0_')[1]
                    if onto_name==namecat:
                        namecat_exist=1
                        namecat_filename=filename
                        break
                if namecat_exist==0:
                    os.makedirs(session['user_folder']+"/ontology/"+str(timeextension)+"_0_"+namecat,exist_ok=True)
                    session['namecat'] = session['user_folder']+"/ontology/"+str(timeextension)+"_0_"+namecat+"/"+namecat
                    if namecat=='addictionnew':
                        with open("addiction.onto","r") as f1:
                            with open(session['namecat']+".onto", "w") as f2:
                                for line in f1:
                                    f2.write(line)
                    else:
                        f= open(session['namecat']+".onto","w")
                        dict_onto={}

                else:
                    session['namecat'] = session['user_folder']+"/ontology/"+namecat_filename+'/'+namecat

                onto_cont=open(session['namecat']+".onto",'r').read()
                if onto_cont=='':
                    dict_onto={}
                else:
                    dict_onto=ast.literal_eval(onto_cont)

                flag_kw=0
                if maincat in dict_onto.keys():  # Layer 2, main category
                    if subcat in dict_onto[maincat].keys():  # Layer 3, keywords shown in results
                        for kw in str.split(next(iter(dict_onto[maincat][subcat])), '|'):
                            keycat_ls = keycat.split('|')
                            for keycat_word in keycat_ls:  # Layer 4, synonyms
                                if kw==keycat_word:
                                    dict_onto[maincat][subcat]=re.sub(r'\|'+keycat_word+'\'', '\'', str(dict_onto[maincat][subcat]))
                                    dict_onto[maincat][subcat]=re.sub(r'\''+keycat_word+'\|', '\'', str(dict_onto[maincat][subcat]))
                                    dict_onto[maincat][subcat]=re.sub(r'\|'+keycat_word+'\|', '|', str(dict_onto[maincat][subcat]))
                                    dict_onto[maincat][subcat]=re.sub(r'\''+keycat_word+'\'', '', str(dict_onto[maincat][subcat]))
                                    flag_kw=1
                        if '{}' in dict_onto[maincat][subcat]:
                            dict_onto[maincat]=re.sub(r', \''+subcat+'\': \'{}\' ', '', str(dict_onto[maincat]))
                            dict_onto[maincat]=re.sub(r'\''+subcat+'\': \'{}\', ', '', str(dict_onto[maincat]))
                            dict_onto[maincat]=re.sub(r'\''+subcat+'\': \'{}\'', '', str(dict_onto[maincat]))
                        if '{}' in dict_onto[maincat]:
                            dict_onto=re.sub(r', \''+maincat+'\': \'{}\'', '', str(dict_onto))
                        dict_onto=str(dict_onto).replace('\"{','{')
                        dict_onto=str(dict_onto).replace('}\"','}')
                        dict_onto=str(dict_onto).replace('\'{','{')
                        dict_onto=str(dict_onto).replace('}\'','}')
                        with open(session['namecat']+'.onto', 'w') as file3:
                            file3.write(str(dict_onto))
                        if flag_kw==0:
                            flash("\""+keycat+"\" is not a keyword.","inval")
                    else:
                        flash("\""+subcat+"\" is not a subcategory.","inval")
                else:
                    flash("\""+subcat+"\" is not a category.","inval")
            else:
                if namecat=='addiction':
                    flash("You must login to change the addiction ontology.")
                else:
                    flash("You must login to create a new ontology.")

    if 'namecat' in session:
        file2 = open(session['namecat']+".onto","r")
        onto_cont=file2.read()
        if onto_cont=='':
            dict_onto={}
        else:
            dict_onto=ast.literal_eval(onto_cont)
    else:
        session['namecat']='addiction'
        file2 = open(session['namecat']+".onto","r")
        onto_cont=file2.read()
        dict_onto=ast.literal_eval(onto_cont)
    name_to_html = str(session['namecat']).split('/')[-1]

    if ('email' in session):
        ontoarchive()
        onto_len_dir = session['onto_len_dir']
        onto_list = session['onto_list']
    else:
        onto_len_dir=0
        onto_list=''
    return render_template('ontology.html',dict_onto=dict_onto, namecat=name_to_html, onto_len_dir=onto_len_dir, onto_list=onto_list,no_footer=True,version=version())


@app.route("/ontoarchive")
def ontoarchive():
    session['onto_len_dir'] = 0
    session['onto_list'] = ''
    if ('email' in session):
        if os.path.exists(datadir+"/user/"+str(session['hashed_email'])+"/ontology") == False:
            flash("Ontology history doesn't exist!")
            onto_len_dir = 0
            onto_list = ''
            onto_cont=open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())
        else:
            session['user_folder'] = datadir+"/user/"+str(session['hashed_email'])
    else:
        flash("You logged out!")
        onto_len_dir = 0
        onto_list = ''
        onto_cont=open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
        return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())

    session_id=session['id']
    def sorted_alphanumeric(data):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
        return sorted(data, key=alphanum_key)

    dirlist = sorted_alphanumeric(os.listdir(session['user_folder']+"/ontology/"))
    onto_folder_list = []
    onto_directory_list = []
    onto_list=[]

    for filename in dirlist:
        onto_folder_list.append(filename)
        onto_name = filename.split('_0_')[1]
        onto_name = onto_name.replace('_', ', ')
        onto_list.append(onto_name)
        onto_name=""
        filename=filename[0:4]+"-"+filename[5:7]+"-"+filename[8:13]+":"+filename[14:16]+":"+filename[17:19]
        onto_directory_list.append(filename)

    onto_len_dir = len(onto_directory_list)
    session['onto_len_dir'] = onto_len_dir
    session['onto_list'] = onto_list
    message3="<ul><li> Click on the Date/Time to view archived results. <li>The Date/Time are based on US Central time zone.</ul> "
    return render_template('ontoarchive.html', onto_len_dir=onto_len_dir, onto_list = onto_list, onto_folder_list=onto_folder_list, onto_directory_list=onto_directory_list, session_id=session_id, message3=message3,version=version())


# Remove an ontology folder
@app.route('/removeonto', methods=['GET', 'POST'])
def removeonto():
    if('email' in session):
        remove_folder = request.args.get('remove_folder')
        shutil.rmtree(datadir+"/user/"+str(session['hashed_email']+"/ontology/"+remove_folder), ignore_errors=True)
        return redirect(url_for('ontoarchive'))
    else:
        flash("You logged out!")
        onto_len_dir = 0
        onto_list = ''
        onto_cont=open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
        return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())


@app.route('/progress')
def progress():
    genes=request.args.get('query')
    genes=genes.replace(",", " ")
    genes=genes.replace(";", " ")
    genes=re.sub(r'\bLOC\d*?\b', "", genes, flags=re.I)
    genes=genes.replace(" \'", " \"")
    genes=genes.replace("\' ", "\" ")
    genes=genes.replace("\'", "-")
    genes1 = [f[1:-1] for f in re.findall('".+?"', genes)]
    genes2 = [p for p in re.findall(r'([^""]+)',genes) if p not in genes1]
    genes2_str = ''.join(genes2)
    genes2 = genes2_str.split()
    genes3 = genes1 + genes2
    genes = [re.sub("\s+", '-', s) for s in genes3]

    # Only 1-200 terms are allowed
    if len(genes)>=200:
        if ('email' in session):
            onto_len_dir = session['onto_len_dir']
            onto_list = session['onto_list']
        else:
            onto_len_dir = 0
            onto_list = ''
        onto_cont=open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
        message="<span class='text-danger'>Up to 200 terms can be searched at a time</span>"
        return render_template('index.html' ,onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto, message=message,version=version())

    if len(genes)==0:
        if ('email' in session):
            onto_len_dir = session['onto_len_dir']
            onto_list = session['onto_list']
        else:
            onto_len_dir = 0
            onto_list = ''
        onto_cont=open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
        message="<span class='text-danger'>Please enter a search term </span>"
        return render_template('index.html',onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto, message=message,version=version())

    tf_path=tempfile.gettempdir()
    genes_for_folder_name =""
    if len(genes) == 1:
        marker = ""
        genes_for_folder_name =str(genes[0])
    elif len(genes) == 2:
        marker = ""
        genes_for_folder_name =str(genes[0])+"_"+str(genes[1])
    elif len(genes) == 3:
        marker = ""
        genes_for_folder_name =str(genes[0])+"_"+str(genes[1])+"_"+str(genes[2])
    else:
        genes_for_folder_name =str(genes[0])+"_"+str(genes[1])+"_"+str(genes[2])
        marker="_m"

    # Generate a unique session ID depending on timestamp to track the results
    timestamp = datetime.utcnow().replace(microsecond=0)
    timestamp = timestamp.replace(tzinfo=pytz.utc)
    timestamp = timestamp.astimezone(pytz.timezone("America/Chicago"))
    timeextension = str(timestamp)
    timeextension = timeextension.replace(':', '_')
    timeextension = timeextension.replace('-', '_')
    timeextension = timeextension.replace(' ', '_')
    timeextension = timeextension.replace('_06_00', '')
    session['timeextension'] = timeextension
    namecat_exist=0

    # Create a folder for the search
    if ('email' in session):
        try:
            namecat=session['namecat']
        except:
            namecat = 'addiction'
            session['namecat'] = namecat
        if namecat=='choose your ontology' or namecat=='addiction' or namecat == 'addiction': # Redundant 'addiction' check
            session['namecat']='addiction'
            onto_cont=open("addiction.onto","r").read()
            # dictionary=ast.literal_eval(onto_cont) # dictionary is global, no need to re-assign from local onto_cont
            search_type = request.args.getlist('type')
            if (search_type == []):
                search_type = ['GWAS', 'function', 'addiction', 'drug', 'brain', 'stress', 'psychiatric', 'cell']
            session['search_type'] = search_type
        else:
            dirlist = os.listdir(session['user_folder']+"/ontology/")
            for filename in dirlist:
                onto_name = filename.split('_0_')[1]
                if onto_name==namecat:
                    namecat_exist=1
                    namecat_filename=filename
                    break
            if (namecat_exist==1):
                session['namecat'] = session['user_folder']+"/ontology/"+namecat_filename+'/'+namecat
                onto_cont=open(session['namecat']+".onto","r").read()
                dict_onto=ast.literal_eval(onto_cont)
                search_type = request.args.getlist('type')
                if (search_type == []):
                    search_type = list(dict_onto.keys())
                session['search_type'] = search_type

        # Save the ontology name in the user search history table
        if session['namecat']=='addiction':
            onto_name_archive = session['namecat']
        elif ('/' in session['namecat']):
            onto_name_archive = session['namecat'].split('/')[-1]
        else:
            onto_name_archive = '-'

        os.makedirs(datadir + "/user/"+str(session['hashed_email'])+"/"+str(timeextension)+"_0_"+genes_for_folder_name+marker+"_0_"+onto_name_archive,exist_ok=True)
        session['path_user'] = datadir+"/user/"+str(session['hashed_email'])+"/"+str(timeextension)+"_0_"+genes_for_folder_name+marker+"_0_"+onto_name_archive+"/"
        session['rnd'] = timeextension+"_0_"+genes_for_folder_name+marker+"_0_"+onto_name_archive
        rnd = session['rnd']
    else:
        rnd = "tmp" + ''.join(random.choice(string.ascii_letters) for x in range(6))
        session['path']=tf_path+ "/" + rnd
        os.makedirs(session['path'])
        search_type = request.args.getlist('type')

        if (search_type == []):
            search_type = ['GWAS', 'function', 'addiction', 'drug', 'brain', 'stress', 'psychiatric', 'cell']
        session['search_type'] = search_type
    genes_session = ''

    for gen in genes:
        genes_session += str(gen) + "_"
    genes_session = genes_session[:-1]
    session['query']=genes
    return render_template('progress.html', url_in="search", url_out="cytoscape/?rnd="+rnd+"&genequery="+genes_session,version=version())


@app.route("/search")
def search():
    genes=session['query']
    percent_ratio=len(genes)+1

    if(len(genes)==1):
        percent_ratio=2
    timeextension=session['timeextension']
    percent=100/percent_ratio-0.00000001 # 7 categories + 1 at the beginning

    if ('email' in session):
        sessionpath = session['path_user'] + timeextension
        path_user=session['path_user']
    else:
        sessionpath = session['path']
        path_user=session['path']+"/"

    snt_file=sessionpath+"_snt"
    cysdata=open(sessionpath+"_cy","w+")
    sntdata=open(snt_file,"w+")
    zeroLinkNode=open(sessionpath+"_0link","w+")
    search_type = session['search_type']
    temp_nodes = ""
    json_nodes = "{\"data\":["

    n_num=0
    d={}
    nodecolor={}
    nodecolor['GWAS'] = "hsl(0, 0%, 70%)"
    nodes_list = []

    if 'namecat' in session:
        namecat_flag=1
        ses_namecat = session['namecat']
        onto_cont = open(session['namecat']+".onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)

        for ky in dict_onto.keys():
            nodecolor[ky] = "hsl("+str((n_num+1)*int(360/len(dict_onto.keys())))+", 70%, 80%)"
            d["nj{0}".format(n_num)]=generate_nodes_json(dict_onto[ky],str(ky),nodecolor[ky])
            n_num+=1

            if (ky in search_type):
                temp_nodes += generate_nodes(dict_onto[ky],str(ky),nodecolor[ky])

                for nd in dict_onto[ky]:
                    nodes_list.append(nd)
                json_nodes += generate_nodes_json(dict_onto[ky],str(ky),nodecolor[ky] )
        d["nj{0}".format(n_num)]=''
    else:
        namecat_flag=0
        for ky in dictionary.keys(): # Using global 'dictionary'
            nodecolor[ky] = "hsl("+str((n_num+1)*int(360/len(dictionary.keys())))+", 70%, 80%)"
            d["nj{0}".format(n_num)]=generate_nodes_json(dictionary[ky],str(ky),nodecolor[ky])
            n_num+=1

            if (ky in search_type):
                temp_nodes += generate_nodes(dictionary[ky],str(ky),nodecolor[ky])

                for nd in dictionary[ky]:
                    nodes_list.append(nd)
                json_nodes += generate_nodes_json(dictionary[ky],str(ky),nodecolor[ky])
        d["nj{0}".format(n_num)]=''

    json_nodes = json_nodes[:-2] # Handles case if json_nodes was only "{\"data\":["
    if json_nodes == "{\"data\"": # if it was empty before -2
        json_nodes = "{\"data\":[]}"
    else:
        json_nodes =json_nodes+"]}"

    def generate(genes, tf_name): # tf_name is snt_file
        with app.test_request_context():
            from nltk.tokenize import sent_tokenize # Moved import here, as it's only used in this function scope.
            sentences=str()
            edges=str()
            nodes = temp_nodes
            progress=0
            searchCnt=0
            nodesToHide=str()
            json_edges = str()
            #genes_or = ' [tiab] or '.join(genes)
            all_d=''

            current_dict_onto = {} # To hold the relevant ontology for this search pass
            if namecat_flag==1:
                onto_cont_local = open(ses_namecat+".onto","r").read() # ses_namecat from outer scope
                current_dict_onto=ast.literal_eval(onto_cont_local)
            else:
                current_dict_onto = dictionary # Use global dictionary

            for ky in current_dict_onto.keys():
                if (ky in search_type):
                    all_d_ls=undic(list(current_dict_onto[ky].values()))
                    all_d = all_d+'|'+all_d_ls
            if all_d: # Check if all_d is not empty
                all_d=all_d[1:]

            if ("GWAS" in search_type):
                datf = pd.read_csv('./utility/gwas_used.csv',sep='\t')
            progress+=percent
            yield "data:"+str(progress)+"\n\n"

            for gene in genes:
                print(f"Fetching info for gene {gene}\n")
                abstracts_raw = getabstracts(gene,all_d) # all_d might be empty if no search_type matches
                print(abstracts_raw)
                sentences_ls=[]

                for row in abstracts_raw.split("\n"):
                    if not row.strip(): continue # Skip empty lines
                    tiab=row.split("\t")
                    pmid = tiab.pop(0)
                    tiab_text = " ".join(tiab) # Renamed to avoid conflict
                    sentences_tok = sent_tokenize(tiab_text)
                    for sent_tok in sentences_tok:
                        sent_tok = pmid + ' ' + sent_tok
                        sentences_ls.append(sent_tok)
                gene=gene.replace("-"," ")

                geneEdges = ""

                # Use the already determined current_dict_onto
                # if namecat_flag==1:
                #     onto_cont = open(ses_namecat+".onto","r").read()
                #     dict_onto_loop=ast.literal_eval(onto_cont)
                # else:
                #     dict_onto_loop = dictionary
                dict_onto_loop = current_dict_onto

                for ky in dict_onto_loop.keys():
                    if (ky in search_type):
                        # The special handling for 'addiction' with 'drug' needs careful check of dict_onto_loop structure
                        if (ky=='addiction') and ('addiction' in dict_onto_loop.keys())\
                            and ('drug' in dict_onto_loop.keys()) and ('addiction' in dict_onto_loop['addiction'].keys())\
                            and ('aversion' in dict_onto_loop['addiction'].keys()) and ('intoxication' in dict_onto_loop['addiction'].keys()):
                            addiction_flag=1
                            # addiction_d is not defined here, assume it's a global or from more_functions
                            # This part might need `addiction_d` from `more_functions.py` to be correctly defined.
                            # For now, assuming addiction_d is available in the scope.
                            sent=gene_category(gene, addiction_d, "addiction", sentences_ls,addiction_flag,dict_onto_loop)
                            if ('addiction' in search_type): # This check is redundant with outer if
                                geneEdges += generate_edges(sent, tf_name)
                                json_edges += generate_edges_json(sent, tf_name)
                        else:
                            addiction_flag=0
                            sent=gene_category(gene,ky,str(ky), sentences_ls, addiction_flag,dict_onto_loop)
                            yield "data:"+str(progress)+"\n\n"

                            geneEdges += generate_edges(sent, tf_name)
                            json_edges += generate_edges_json(sent, tf_name)
                        sentences+=sent
                if ("GWAS" in search_type and 'GWAS' in dict_onto_loop): # Added check for GWAS in dict_onto_loop
                    gwas_sent=[]
                    # print (datf) # datf is loaded earlier
                    datf_sub1 = datf[datf["MAPPED_GENE"].str.contains('(?:\s|^)'+gene+'(?:\s|$)', flags=re.IGNORECASE, na=False)
                                    | (datf["REPORTED GENE(S)"].str.contains('(?:\s|^)'+gene+'(?:\s|$)', flags=re.IGNORECASE, na=False))]
                    # print (datf_sub1)
                    for nd2 in dict_onto_loop['GWAS'].keys():
                        # Ensure dict_onto_loop['GWAS'][nd2] is iterable and contains strings
                        # Example: if dict_onto_loop['GWAS'][nd2] is {'keyword1|keyword2'}
                        # next(iter(dict_onto_loop['GWAS'][nd2])) might be what was intended
                        # Assuming dict_onto_loop['GWAS'][nd2] is a set/list of keyword strings like {'kw1|kw2', 'kw3'}
                        # The original code was: for nd1 in dict_onto_loop['GWAS'][nd2]: for nd in nd1.split('|'):
                        # This implies dict_onto_loop['GWAS'][nd2] contains combined keywords.
                        # Let's assume the structure is { 'subcategory' : {'keyword_group1', 'keyword_group2'} }
                        # where keyword_group is "termA|termB"

                        # Iterating over the values of the sub-dictionary if it's a dict, or elements if it's a list/set
                        sub_keywords_container = dict_onto_loop['GWAS'][nd2]
                        # This needs to be robust to the actual structure of dict_onto_loop['GWAS'][nd2]
                        # Assuming it's a set of strings, where each string can be pipe-separated.
                        # e.g., sub_keywords_container = {'phenotype1|phenotype_alias', 'phenotype2'}
                        actual_keywords_to_iterate = []
                        if isinstance(sub_keywords_container, dict): # e.g. {'phenotype_group': 'pheno1|pheno2'}
                             for key_group_str in sub_keywords_container.values(): # Or .keys() if that's the intent
                                actual_keywords_to_iterate.extend(key_group_str.split('|'))
                        elif isinstance(sub_keywords_container, (list, set)):
                            for key_group_str in sub_keywords_container:
                                actual_keywords_to_iterate.extend(key_group_str.split('|'))
                        elif isinstance(sub_keywords_container, str): # e.g. 'pheno1|pheno2'
                            actual_keywords_to_iterate.extend(sub_keywords_container.split('|'))


                        for nd in actual_keywords_to_iterate:
                            gwas_text=''
                            # Added na=False to contains calls
                            datf_sub = datf_sub1[datf_sub1['DISEASE/TRAIT'].str.contains('(?:\s|^)'+nd+'(?:\s|$)', flags=re.IGNORECASE, na=False)]
                            if not datf_sub.empty:
                                for index, row in datf_sub.iterrows():
                                    gwas_text = f"SNP:{row['SNPS']}, P value: {row['P-VALUE']}, Disease/trait: {row['DISEASE/TRAIT']}, Mapped trait: {row['MAPPED_TRAIT']}"
                                    gwas_sent.append(gene+"\t"+"GWAS"+"\t"+nd2+"_GWAS\t"+str(row['PUBMEDID'])+"\t"+gwas_text) # Changed nd to nd2 for target node
                    cys, gwas_json, sn_file = searchArchived('GWAS', gene , 'json',gwas_sent, path_user)
                    with open(path_user+"gwas_results.tab", "a") as gwas_edges:
                        gwas_edges.write(sn_file)
                    geneEdges += cys
                    json_edges += gwas_json
                # report progress immediately
                progress+=percent
                yield "data:"+str(progress)+"\n\n"

                if len(geneEdges) >0:
                    rnd = ''
                    if 'email' in session:
                        if 'rnd' in session:
                            rnd = session['rnd']
                        elif 'path_user' in session:
                            rnd = session['path_user'].split('/')[-2]
                    elif 'path' in session:
                        rnd = session['path'].split('/')[-1]

                    edges+=geneEdges
                    nodes+="{ data: { id: '" + gene +  "', nodecolor:'#E74C3C', fontweight:700, url:'/synonyms?node="+gene+"&rnd="+rnd+"'} },\n"
                else:
                    nodesToHide+=gene +  " "

                searchCnt+=1
                if (searchCnt==len(genes)):
                    progress=100
                    sntdata.write(sentences)
                    sntdata.close()
                    cysdata.write(nodes+edges)
                    cysdata.close()
                    zeroLinkNode.write(nodesToHide)
                    zeroLinkNode.close()
                yield "data:"+str(progress)+"\n\n"

                        # Edges in json format
            json_edges_content = json_edges.strip()
            if json_edges_content.endswith(','):
                json_edges_content = json_edges_content[:-1]

            if not json_edges_content:
                json_edges = "{\"data\":[]}"
            else:
                json_edges = "{\"data\":[" + json_edges_content + "]}"

            # Write edges to txt file in json format also in user folder
            with open(path_user+"edges.json", "w") as temp_file_edges:
                temp_file_edges.write(json_edges)

    with open(path_user+"nodes.json", "w") as temp_file_nodes:
        temp_file_nodes.write(json_nodes)
    return Response(generate(genes, snt_file), mimetype='text/event-stream')


@app.route("/tableview/")
def tableview():
    genes_url=request.args.get('genequery')
    rnd_url=request.args.get('rnd')
    tf_path=tempfile.gettempdir()

    if ('email' in session):
        filename = rnd_url.split("_0_")[0]
        genes_session_tmp = datadir+"/user/"+str(session['hashed_email'])+"/"+rnd_url+"/"+filename
        gene_url_tmp = "/user/"+str(session['hashed_email'])+"/"+rnd_url

        try:
            with open(datadir+gene_url_tmp+"/nodes.json") as jsonfile:
                jnodes = json.load(jsonfile)
        except FileNotFoundError:
            flash("You logged out!")
            onto_len_dir = 0
            onto_list = ''
            onto_cont=open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())

        jedges =''
        nodata_temp = 1 # Default to no data
        try:
            with open(datadir+gene_url_tmp +"/edges.json") as edgesjsonfile:
                # Check if file is empty or just contains empty structure
                content = edgesjsonfile.read().strip()
                if content and content != "{\"data\":[]}":
                    # Reset file pointer and load json
                    edgesjsonfile.seek(0)
                    jedges = json.load(edgesjsonfile)
                    nodata_temp = 0
                else:
                    jedges = {"data": []} # Ensure jedges is a dict
        except FileNotFoundError:
            jedges = {"data": []} # Ensure jedges is a dict if file not found
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {datadir+gene_url_tmp}/edges.json")
            jedges = {"data": []} # Ensure jedges is a dict
            nodata_temp = 1


    else:
        genes_session_tmp=tf_path+"/"+rnd_url
        gene_url_tmp = genes_session_tmp
        try:
            with open(gene_url_tmp+"/nodes.json") as jsonfile:
                jnodes = json.load(jsonfile)
        except FileNotFoundError:
            flash("You logged out!")
            onto_len_dir = 0
            onto_list = ''
            onto_cont=open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())

        jedges =''
        nodata_temp = 1 # Default to no data
        try:
            with open(gene_url_tmp +'/edges.json') as edgesjsonfile:
                content = edgesjsonfile.read().strip()
                if content and content != "{\"data\":[]}":
                    edgesjsonfile.seek(0)
                    jedges = json.load(edgesjsonfile)
                    nodata_temp = 0
                else:
                    jedges = {"data": []}
        except FileNotFoundError:
             jedges = {"data": []}
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {gene_url_tmp}/edges.json")
            jedges = {"data": []}
            nodata_temp = 1

    genename=genes_url.split("_")
    if len(genename)>3:
        genename = genename[0:3]
        added = ",..."
    else:
        added = ""
    gene_name = str(genename)[1:]
    gene_name=gene_name[:-1]
    gene_name=gene_name.replace("'","")
    gene_name = gene_name+added
    num_gene = gene_name.count(',')+1

    message3="<ul><li> <font color=\"#E74C3C\">Click on the abstract count to read sentences linking the keyword and the gene</font>  <li> Click on a keyword to see the terms included in the search. <li>View the results in <a href='\\cytoscape/?rnd={}&genequery={}'\ ><b> a graph.</b></a> </ul> Links will be preserved when the table is copy-n-pasted into a spreadsheet.".format(rnd_url,genes_url)
    return render_template('tableview.html', genes_session_tmp = genes_session_tmp, nodata_temp=nodata_temp, num_gene=num_gene, jedges=jedges, jnodes=jnodes,gene_name=gene_name, message3=message3, rnd_url=rnd_url, genes_url=genes_url,no_footer=True,version=version())


# Table for the zero abstract counts
@app.route("/tableview0/")
def tableview0():
    genes_url=request.args.get('genequery')
    rnd_url=request.args.get('rnd')
    tf_path=tempfile.gettempdir()

    if ('email' in session):
        filename = rnd_url.split("_0_")[0]
        # genes_session_tmp = datadir+"/user/"+str(session['hashed_email'])+"/"+rnd_url+"/"+filename # Not used further
        gene_url_tmp = "/user/"+str(session['hashed_email'])+"/"+rnd_url
        try:
            with open(datadir+gene_url_tmp+"/nodes.json") as jsonfile:
                jnodes = json.load(jsonfile)
        except FileNotFoundError:
            flash("You logged out!")
            onto_len_dir = 0
            onto_list = ''
            onto_cont=open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())

        jedges =''
        nodata_temp = 1 # Default to no data
        try:
            with open(datadir+gene_url_tmp +'/edges.json') as edgesjsonfile:
                content = edgesjsonfile.read().strip()
                if content and content != "{\"data\":[]}":
                    edgesjsonfile.seek(0)
                    jedges = json.load(edgesjsonfile)
                    nodata_temp = 0
                else:
                    jedges = {"data": []}
        except FileNotFoundError:
             jedges = {"data": []}
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {datadir+gene_url_tmp}/edges.json")
            jedges = {"data": []}
            nodata_temp = 1

    else:
        # genes_session_tmp=tf_path+"/"+rnd_url # Not used further
        gene_url_tmp = tf_path+"/"+rnd_url
        try:
            with open(gene_url_tmp+"/nodes.json") as jsonfile:
                jnodes = json.load(jsonfile)
        except FileNotFoundError:
            flash("You logged out!")
            onto_len_dir = 0
            onto_list = ''
            onto_cont=open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())

        jedges =''
        nodata_temp = 1 # Default to no data
        try:
            with open(gene_url_tmp +'/edges.json') as edgesjsonfile:
                content = edgesjsonfile.read().strip()
                if content and content != "{\"data\":[]}":
                    edgesjsonfile.seek(0)
                    jedges = json.load(edgesjsonfile)
                    nodata_temp = 0
                else:
                    jedges = {"data": []}
        except FileNotFoundError:
            jedges = {"data": []}
        except json.JSONDecodeError:
            print(f"Warning: Could not decode JSON from {gene_url_tmp}/edges.json")
            jedges = {"data": []}
            nodata_temp = 1

    genes_url=request.args.get('genequery')
    genename=genes_url.split("_")
    if len(genename)>3:
        genename = genename[0:3]
        added = ",..."
    else:
        added = ""

    gene_name = str(genename)[1:]
    gene_name=gene_name[:-1]
    gene_name=gene_name.replace("'","")
    gene_name = gene_name+added
    num_gene = gene_name.count(',')+1
    message4="<b> Notes: </b><li> These are the keywords that have <b>zero</b> abstract counts. <li>View all the results in <a href='\\cytoscape/?rnd={}&genequery={}'><b> a graph.</b></a> ".format(rnd_url,genes_url)
    return render_template('tableview0.html',nodata_temp=nodata_temp, num_gene=num_gene, jedges=jedges, jnodes=jnodes,gene_name=gene_name, message4=message4,version=version())


@app.route("/userarchive")
def userarchive():
    onto_len_dir = 0
    onto_list = ''
    onto_cont=open("addiction.onto","r").read()
    dict_onto=ast.literal_eval(onto_cont)

    if ('email' in session):
        if os.path.exists(datadir+"/user/"+str(session['hashed_email'])) == False:
            flash("Search history doesn't exist!")
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())
        else:
            session['user_folder'] = datadir+"/user/"+str(session['hashed_email'])
    else:
        # onto_name_archive='' # This variable is not used here
        flash("You logged out!")
        onto_len_dir = 0
        onto_list = ''
        onto_cont=open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
        return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())

    session_id=session['id']
    def sorted_alphanumeric(data):
        convert = lambda text: int(text) if text.isdigit() else text.lower()
        alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ]
        return sorted(data, key=alphanum_key)
    dirlist = sorted_alphanumeric(os.listdir(session['user_folder']))
    folder_list = []
    directory_list = []
    gene_list=[]
    onto_list_archive =[] # Renamed to avoid conflict with outer scope 'onto_list'

    for filename in dirlist:
        if ('_0_'  in filename): # Ensure it's a search result folder, not e.g. "ontology"
            if os.path.isdir(os.path.join(session['user_folder'], filename)): # Check if it's a directory
                folder_list.append(filename)
                try:
                    gene_name = filename.split('_0_')[1]
                    onto_name = filename.split('_0_')[2]
                    if gene_name.endswith('_m'): # Check using endswith for robustness
                        gene_name = gene_name[:-2]
                        gene_name = gene_name + ", ..."
                    gene_name = gene_name.replace('_', ', ')
                    gene_list.append(gene_name)
                    onto_list_archive.append(onto_name) # Use renamed list
                    # onto_name="" # Not necessary, re-assigned in loop
                    # gene_name="" # Not necessary, re-assigned in loop
                    # Format filename for display
                    display_filename=filename.split('_0_')[0] # Get only the timestamp part for display formatting
                    display_filename=display_filename[0:4]+"-"+display_filename[5:7]+"-"+display_filename[8:10]+" "+display_filename[11:13]+":"+display_filename[14:16]+":"+display_filename[17:19]
                    directory_list.append(display_filename)
                except IndexError:
                    print(f"Skipping folder with unexpected name format: {filename}")
                    continue

    len_dir = len(directory_list)
    message3="<ul><li> Click on the Date/Time to view archived results. <li>The Date/Time are based on US Central time zone.</ul> "
    return render_template('userarchive.html', len_dir=len_dir, gene_list = gene_list, onto_list = onto_list_archive, folder_list=folder_list, directory_list=directory_list, session_id=session_id, message3=message3,version=version())


# Remove the search directory
@app.route('/remove', methods=['GET', 'POST'])
def remove():
    if('email' in session):
        remove_folder = request.args.get('remove_folder')
        shutil.rmtree(datadir+"/user/"+str(session['hashed_email']+"/"+remove_folder), ignore_errors=True)
        return redirect(url_for('userarchive'))
    else:
        flash("You logged out!")
        onto_len_dir = 0
        onto_list = ''
        onto_cont=open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
        return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list, ontol = 'addiction', dict_onto = dict_onto,version=version())


@app.route('/date', methods=['GET', 'POST'])
def date():
    select_date = request.args.get('selected_date')
    # Open the cache folder for the user
    tf_path=datadir+"/user" # tf_path is effectively datadir+"/user"
    nodata_temp = 1 # Default to no data
    jedges = {"data": []} # Default empty jedges
    jnodes = {"data": []} # Default empty jnodes
    gene_list_all = []
    gene_name = "N/A"
    num_gene = 0

    if ('email' in session):
        time_extension = str(select_date).split('_0_')[0]
        # gene_name1 = str(select_date).split('_0_')[1] # Not used directly for fetching, gene list derived from edges
        # time_extension = time_extension.replace(':', '_') # This was for folder creation, not reading
        # time_extension = time_extension.replace('-', '_')
        session['user_folder'] = tf_path+"/"+str(session['hashed_email']) # This seems redundant here
        genes_session_tmp = tf_path+"/"+str(session['hashed_email'])+"/"+select_date+"/"+time_extension # This path is for the _snt, _cy files etc.

        try:
            with open(tf_path+"/"+str(session['hashed_email'])+"/"+select_date+"/nodes.json", "r") as jsonfile:
                jnodes = json.load(jsonfile)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading nodes.json: {e}")
            # Keep default jnodes

        try:
            with open(tf_path+"/"+str(session['hashed_email'])+"/"+select_date+"/edges.json", "r") as edgesjsonfile:
                content = edgesjsonfile.read().strip()
                if content and content != "{\"data\":[]}":
                    edgesjsonfile.seek(0)
                    jedges = json.load(edgesjsonfile)
                    nodata_temp = 0
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading edges.json: {e}")
            # Keep default jedges and nodata_temp = 1

        if nodata_temp == 0 and jedges.get("data"):
            current_gene_list = []
            for p in jedges['data']:
                if p['source'] not in current_gene_list:
                    gene_list_all.append(p['source'])
                    current_gene_list.append(p['source'])

            display_gene_list = current_gene_list
            added = ""
            if len(current_gene_list)>3:
                display_gene_list = current_gene_list[0:3]
                added = ",..."

            gene_name_str = str(display_gene_list)[1:-1] # Remove brackets
            gene_name_str=gene_name_str.replace("'","")
            gene_name = gene_name_str + added
            num_gene = len(current_gene_list) # Count of unique source genes
        else: # No data or error, try to get gene name from folder
            try:
                gene_name_from_folder = str(select_date).split('_0_')[1]
                if gene_name_from_folder.endswith("_m"):
                    gene_name_from_folder = gene_name_from_folder[:-2] + ", ..."
                gene_name = gene_name_from_folder.replace("_", ", ")
                num_gene = gene_name.count(',') + 1
                gene_list_all = gene_name.split(', ') # Approximate
            except IndexError:
                gene_name = "N/A"
                num_gene = 0

        genes_session_str = '' # Renamed to avoid conflict
        for gen_item in gene_list_all: # Use gene_list_all derived from edges if possible
            genes_session_str += str(gen_item).strip() + "_" # Ensure clean gene names
        if genes_session_str:
            genes_session_str = genes_session_str[:-1]

    else:
        flash("You logged out!")
        onto_len_dir = 0
        onto_list_session = '' # Renamed to avoid conflict
        onto_cont=open("addiction.onto","r").read()
        dict_onto=ast.literal_eval(onto_cont)
        return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list_session, ontol = 'addiction', dict_onto = dict_onto,version=version())

    message3="<ul><li> <font color=\"#E74C3C\">Click on the abstract count to read sentences linking the keyword and the gene</font> <li> Click on a keyword to see the terms included in the search. <li>View the results in <a href='\\cytoscape/?rnd={}&genequery={}'\ ><b> a graph.</b></a> </ul> Links will be preserved when the table is copy-n-pasted into a spreadsheet.".format(select_date,genes_session_str)
    return render_template('tableview.html',nodata_temp=nodata_temp, num_gene=num_gene,genes_session_tmp = genes_session_tmp, rnd_url=select_date ,jedges=jedges, jnodes=jnodes,gene_name=gene_name, genes_url=genes_session_str, message3=message3,no_footer=True,version=version())

@app.route('/cytoscape/')
def cytoscape():
    genes_url=request.args.get('genequery')
    rnd_url=request.args.get('rnd')
    tf_path=tempfile.gettempdir()
    # genes_session_tmp=tf_path + "/" + genes_url # This variable is not used
    # rnd_url_tmp=tf_path +"/" + rnd_url # This is for non-logged in users path later
    message2="<ul><li><font color=\"#E74C3C\">Click on a line to read the sentences </font> <li>Click on a keyword to see the terms included in the search<li>Hover a pointer over a node to hide other links <li>Move the nodes around to adjust visibility <li> Reload the page to restore the default layout<li>View the results in <a href='\\tableview/?rnd={}&genequery={}'\ ><b>a table. </b></a></ul>".format(rnd_url,genes_url)

    elements = "" # Default empty elements
    zeroLink = "" # Default empty zeroLink

    if ('email' in session):
        filename_part = rnd_url.split("_0_")[0] # Corrected variable name
        rnd_url_path = datadir+"/user/"+str(session['hashed_email'])+"/"+rnd_url+"/"+filename_part # Corrected variable name
        try:
            with open(rnd_url_path+"_cy","r") as f:
                elements=f.read()
        except FileNotFoundError:
            flash("You logged out or the search data is missing!") # More specific message
            onto_len_dir = 0
            onto_list_session = '' # Renamed
            onto_cont=open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list_session, ontol = 'addiction', dict_onto = dict_onto,version=version())

        try:
            with open(rnd_url_path+"_0link","r") as z:
                zeroLink=z.read()
        except FileNotFoundError:
            zeroLink = "" # File might not exist if no zero link genes

    else: # Not logged in, use temp path
        rnd_url_path=tf_path +"/" + rnd_url
        try:
            # rnd_url_path.replace("\"", "") # This doesn't modify in place and is likely not needed
            with open(rnd_url_path+"_cy","r") as f:
                elements=f.read()
        except FileNotFoundError:
            flash("You logged out or the search data is missing!")
            onto_len_dir = 0
            onto_list_session = '' # Renamed
            onto_cont=open("addiction.onto","r").read()
            dict_onto=ast.literal_eval(onto_cont)
            return render_template('index.html', onto_len_dir=onto_len_dir, onto_list=onto_list_session, ontol = 'addiction', dict_onto = dict_onto,version=version())

        try:
            with open(rnd_url_path+"_0link","r") as z:
                zeroLink=z.read()
        except FileNotFoundError:
            zeroLink = ""

    if (len(zeroLink.strip())>0): # Check if zeroLink has content after stripping whitespace
        message2+="<span style=\"color:darkred;\">No result was found for these genes: " + zeroLink + "</span>"

    return render_template('cytoscape.html', elements=elements, message2=message2,version=version())


@app.route("/sentences")
def sentences():
    # Removed predict_sent and CNN model loading
    # def predict_sent(sent_for_pred): ...

    pmid_list=[]
    pmid_string=''
    edge=request.args.get('edgeID')
    (tf_name, gene0, cat0)=edge.split("|")

    out3=""
    out_pos = ""
    out_neg = ""
    num_abstract = 0
    stress_cellular = "<br><br><br>"+"</ol><b>Sentence(s) describing cellular stress (classified using Gemini API):</b><hr><ol>"
    stress_systemic = "<b></ol>Sentence(s) describing systemic stress (classified using Gemini API):</b><hr><ol>"

    matching_sents = get_sentences_from_file(tf_name, gene0, cat0)
    if not matching_sents:
        # It's possible the file was found but no sentences matched the criteria.
        return render_template('sentences.html', sentences=f"<p>No sentences found for {gene0} and {cat0}.</p>",no_footer=True,version=version())

    all_stress_sentences = []
    num_abstract = len(matching_sents)

    for sent_obj in matching_sents:
        text = sent_obj['text']
        pmid = sent_obj['pmid']

        formatted_line = f"<li> {text} <a href=\"https://www.ncbi.nlm.nih.gov/pubmed/?term={pmid}\" target=_new>PMID:{pmid}<br></a>"
        all_stress_sentences.append({'raw_text': text, 'html_line': formatted_line})

        out3 += formatted_line
        if(pmid+cat0 not in pmid_list):
            pmid_string = pmid_string + ' ' + pmid
            pmid_list.append(pmid+cat0)

    # Step 2: If the category is 'stress' and we have sentences, perform batch classification
    if cat0 == 'stress' and all_stress_sentences:
        if not GEMINI_API_KEY:
            print("Gemini API key not configured. Skipping batch classification.")
        else:
            try:
                # Create the batched prompt
                sentences_to_classify_str = ""
                for i, s_obj in enumerate(all_stress_sentences):
                    # Use a unique, parsable identifier for each sentence
                    sentences_to_classify_str += f'Sentence {i}: "{s_obj["raw_text"]}"\n'

                batched_prompt = f"""For each sentence below, classify it as describing "Cellular Stress" or "Organismal Stress".
Return your response as a valid JSON object where keys are the sentence numbers (e.g., "0", "1", "2") and values are the classification ("Cellular Stress" or "Organismal Stress").

Example format: {{"0": "Cellular Stress", "1": "Organismal Stress"}}

Here are the sentences to classify:
{sentences_to_classify_str}
"""
                # Call the API using the new Client
                print(f"Gemini API call: batch stress classification (gemini-3-flash-preview)\n  Prompt: {batched_prompt}")
                response = gemini_client.models.generate_content(
                    model='gemini-3-flash-preview',
                    contents=batched_prompt
                )
                print(f"  Gemini response: {response.text.strip()}")

                # Step 3: Parse the JSON response
                # The model might wrap the JSON in ```json ... ```, so we need to clean it.
                cleaned_response_text = response.text.strip().replace("```json", "").replace("```", "").strip()
                classifications = json.loads(cleaned_response_text)

                # Step 4: Distribute the sentences into buckets based on the parsed classifications
                for i, s_obj in enumerate(all_stress_sentences):
                    # Get the classification for sentence 'i'. Use .get() for safety.
                    classification = classifications.get(str(i), "unknown").lower()
                    if "cellular" in classification:
                        out_neg += s_obj['html_line']
                    elif "organismal" in classification:
                        out_pos += s_obj['html_line']

            except Exception as e:
                print(f"Error during batch Gemini classification: {e}")
    out1="<h3>"+gene0 + " and " + cat0  + "</h3>\n"
    if len(pmid_list)>1:
        out2 = str(num_abstract) + ' sentences in ' + " <a href=\"https://www.ncbi.nlm.nih.gov/pubmed/?term=" + pmid_string.strip() +"\" target=_new>"+ str(len(pmid_list)) + ' studies' +"<br></a>" + "<br><br>"
    elif len(pmid_list) == 1: # Handle single study case
        out2 = str(num_abstract) + ' sentence(s) in '+ " <a href=\"https://www.ncbi.nlm.nih.gov/pubmed/?term=" + pmid_string.strip() +"\" target=_new>"+ str(len(pmid_list)) + ' study' +"<br></a>" "<br><br>"
    else: # No PMIDs found, num_abstract might still be > 0 if PMIDs were not parsable in file but text matched
        out2 = str(num_abstract) + ' sentence(s) found.<br><br>'


    if(cat0 == 'stress'): # Only show stress classification if category is stress
        if(out_neg == "" and out_pos == ""):
            # If no classification results, show all sentences if any, or a message
            if out3:
                 out= out1+ out2 + "<b>All related sentences (Gemini classification not available or no specific stress types found):</b><hr><ol>" + out3
            else:
                 out = out1 + out2 + "No sentences found for this combination, or Gemini classification yielded no results."
        elif(out_pos != "" and out_neg!=""):
            out = out1 + out2 + stress_systemic+out_pos + stress_cellular + out_neg
        elif(out_pos != "" and out_neg ==""):
            out= out1+ out2 + stress_systemic + out_pos
        elif(out_neg != "" and out_pos == ""):
            out = out1 +out2+stress_cellular+out_neg
    else: # Not stress category, just show all found sentences
        out= out1+ out2 + "<ol>" + out3

    # K.clear_session() # Removed
    return render_template('sentences.html', sentences=out+"</ol><p>",no_footer=True,version=version())


# Show the cytoscape graph for one gene from the top gene list
@app.route("/showTopGene")
def showTopGene():
    query=request.args.get('topGene')
    # Assuming searchArchived returns a tuple, and the first element is nodesEdges
    archived_data = searchArchived('topGene',query, 'cys','','')
    if isinstance(archived_data, tuple) and len(archived_data) > 0:
        nodesEdges = archived_data[0]
    else: # Fallback if searchArchived doesn't return expected tuple
        nodesEdges = ""
        print(f"Warning: searchArchived did not return expected data for {query}")

    message2="<li><strong>"+query + "</strong> is one of the top addiction genes. <li> An archived search is shown. Click on the blue circle to update the results and include keywords for brain region and gene function. <strong> The update may take a long time to finish.</strong> "
    return render_template("cytoscape.html", elements=nodesEdges, message="Top addiction genes", message2=message2,version=version())

'''
@app.route("/shownode")
def shownode():
    node=request.args.get('node')
    out = "" # Default value
    current_dict_onto = {}

    if 'namecat' in session:
        try:
            with open(session['namecat']+".onto","r") as file2:
                onto_cont_local=file2.read()
                current_dict_onto=ast.literal_eval(onto_cont_local)
        except FileNotFoundError:
            print(f"Ontology file not found: {session['namecat']}.onto. Falling back to default.")
            current_dict_onto = dictionary # Fallback to default if custom not found
        except Exception as e:
            print(f"Error loading custom ontology {session['namecat']}.onto: {e}. Falling back to default.")
            current_dict_onto = dictionary
    else:
        current_dict_onto = dictionary # Default global dictionary

    for ky in current_dict_onto.keys():
        if node in current_dict_onto[ky].keys():
            # Ensure current_dict_onto[ky][node] is a dict and has at least one item
            node_details = current_dict_onto[ky][node]
            if isinstance(node_details, dict) and node_details:
                 out="<p>"+node.upper()+"<hr><li>"+ next(iter(node_details)).replace("|", "<li>")
                 break # Found the node, no need to check other keys
            elif isinstance(node_details, str): # If it's just a string of keywords
                 out="<p>"+node.upper()+"<hr><li>"+ node_details.replace("|", "<li>")
                 break
    if not out: # If node not found or details are empty
        out = f"<p>Details for node '{node.upper()}' not found in the current ontology.</p>"

    return render_template('sentences.html', sentences=out+"<p>",no_footer=True,version=version())
'''
@app.route("/shownode")
def shownode():
    node=request.args.get('node')
    if 'namecat' in session:
        file2 = open(session['namecat']+".onto","r")
        onto_cont=file2.read()
        dict_onto=ast.literal_eval(onto_cont)
        for ky in dict_onto.keys():
            if node in dict_onto[ky].keys():
                out="<p>"+node.upper()+"<hr><li>"+ next(iter(dict_onto[ky][node])).replace("|", "<li>")
    else:
        for ky in dictionary.keys():
            if node in dictionary[ky].keys():
                out="<p>"+node.upper()+"<hr><li>"+ next(iter(dictionary[ky][node])).replace("|", "<li>")
    return render_template('sentences.html', sentences=out+"<p>",no_footer=True,version=version())



@app.route("/synonyms")
def synonyms():
    node = request.args.get('node')
    rnd = request.args.get('rnd')

    if not node:
        return "Error: Gene node is required.", 400
    node = node.upper()

    try:
        # --- Part 1: Handle Synonyms Links ---
        allnodes = {}
        if 'genes' in globals() and isinstance(globals()['genes'], dict):
            allnodes = globals()['genes']
        else:
            print("Warning: 'genes' dictionary for synonyms not found.")

        synonym_list = list(allnodes[node].split("|"))
        session['synonym_list'] = synonym_list
        session['main_gene'] = node.upper()
        synonym_list_str = ';'.join([str(syn) for syn in synonym_list])
        synonym_list_str += ';' + node
        case = 1

        formatted_sentences = ""

        if rnd and rnd.strip():
            # --- Logic to use existing search results ---
            print(f"Synonyms: rnd '{rnd}' provided. Reading from search results.")
            path = ''
            if 'email' in session and 'hashed_email' in session:
                path = datadir+"/user/"+str(session['hashed_email'])+"/"+rnd+"/"
            else:
                tf_path = tempfile.gettempdir()
                path = tf_path + "/" + rnd + "/"

            timestamp = rnd.split("_0_")[0]
            snt_file_path = path + timestamp + "_snt"
            gwas_file_path = path + "gwas_results.tab"

            sents_by_main_cat = {}

            try:
                with open(snt_file_path, "r") as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            (l_gene, l_main_cat, l_sub_cat, l_pmid, l_text) = line.strip().split("\t")
                            if l_gene.upper() == node:
                                if l_main_cat not in sents_by_main_cat: sents_by_main_cat[l_main_cat] = {}
                                if l_sub_cat not in sents_by_main_cat[l_main_cat]: sents_by_main_cat[l_main_cat][l_sub_cat] = []
                                sents_by_main_cat[l_main_cat][l_sub_cat].append({'pmid': l_pmid, 'text': l_text})
                        except ValueError: continue
            except FileNotFoundError: print(f"Sentence file not found: {snt_file_path}")

            try:
                with open(gwas_file_path, "r") as f:
                    for line in f:
                        if not line.strip(): continue
                        try:
                            (l_gene, l_main_cat, l_sub_cat, l_pmid, l_text) = line.strip().split("\t")
                            if l_gene.upper() == node:
                                if 'GWAS' not in sents_by_main_cat: sents_by_main_cat['GWAS'] = {}
                                sub_cat_clean = l_sub_cat.replace('_GWAS', '')
                                if sub_cat_clean not in sents_by_main_cat['GWAS']: sents_by_main_cat['GWAS'][sub_cat_clean] = []
                                sents_by_main_cat['GWAS'][sub_cat_clean].append({'pmid': l_pmid, 'text': l_text})
                        except ValueError: continue
            except FileNotFoundError: print(f"GWAS sentence file not found: {gwas_file_path}")

            for main_cat, sub_cats in sorted(sents_by_main_cat.items()):
                for sub_cat, sentences in sorted(sub_cats.items()):
                    formatted_sentences += f"\n## Keyword: {sub_cat} (Category: {main_cat})\n"
                    for sent_obj in sentences:
                        clean_text = re.sub('<[^<]+?>', '', sent_obj['text'])
                        formatted_sentences += f"- {clean_text} (PMID: {sent_obj['pmid']})\n"
        else:
            # --- Fallback Logic: Perform a fresh search ---
            print(f"Synonyms: rnd not provided. Performing fresh search for {node}.")
            current_ontology = {}
            if 'namecat' in session and session['namecat'] != 'addiction' and not session['namecat'].startswith(tempfile.gettempdir()):
                try:
                    with open(session['namecat'] + ".onto", "r") as f_onto: current_ontology = ast.literal_eval(f_onto.read())
                except (FileNotFoundError, SyntaxError, TypeError): current_ontology = dictionary
            else: current_ontology = dictionary

            abstracts_raw = getabstracts(node, "")
            sentences_ls = []
            if abstracts_raw:
                for row in abstracts_raw.split("\n"):
                    if not row.strip(): continue
                    parts = row.split("\t", 1)
                    if len(parts) < 2: continue
                    pmid, tiab_text = parts
                    for sent_tok in sent_tokenize(tiab_text): sentences_ls.append({'pmid': pmid, 'text': sent_tok})

            pubmed_formatted_sentences = ""
            if sentences_ls:
                gene_regex = re.compile(r'\b(' + re.escape(node) + r')\b', re.IGNORECASE)
                for category_key, keyword_nodes in sorted(current_ontology.items()):
                    if not isinstance(keyword_nodes, dict): continue
                    for keyword_node, search_terms_obj in sorted(keyword_nodes.items()):
                        if isinstance(search_terms_obj, set) and search_terms_obj: search_terms_str = next(iter(search_terms_obj))
                        elif isinstance(search_terms_obj, str): search_terms_str = search_terms_obj
                        else: continue

                        keyword_regex_str = r'\b(' + '|'.join(re.escape(term) for term in search_terms_str.split('|')) + r')\b'
                        keyword_regex = re.compile(keyword_regex_str, re.IGNORECASE)

                        sents_for_this_keyword = [s for s in sentences_ls if gene_regex.search(s['text']) and keyword_regex.search(s['text'])]

                        if sents_for_this_keyword:
                            pubmed_formatted_sentences += f"\n## Keyword: {keyword_node} (Category: {category_key})\n"
                            for sent_obj in sents_for_this_keyword: pubmed_formatted_sentences += f"- {sent_obj['text']} (PMID: {sent_obj['pmid']})\n"

            gwas_formatted_sentences = ""
            if 'GWAS' in current_ontology:
                try:
                    datf = pd.read_csv('./utility/gwas_used.csv', sep='\t')
                    gene_pattern = r'(?:\s|^)' + re.escape(node) + r'(?:\s|$)'
                    datf_sub1 = datf[datf["MAPPED_GENE"].str.contains(gene_pattern, flags=re.IGNORECASE, na=False) | datf["REPORTED GENE(S)"].str.contains(gene_pattern, flags=re.IGNORECASE, na=False)]
                    if not datf_sub1.empty:
                        gwas_sents_for_node = []
                        gwas_ontology_part = current_ontology.get('GWAS', {})
                        if isinstance(gwas_ontology_part, dict):
                            for keyword_node, search_terms_obj in sorted(gwas_ontology_part.items()):
                                if isinstance(search_terms_obj, set) and search_terms_obj: search_terms_str = next(iter(search_terms_obj))
                                elif isinstance(search_terms_obj, str): search_terms_str = search_terms_obj
                                else: continue
                                for term in search_terms_str.split('|'):
                                    if not term: continue
                                    term_pattern = r'(?:\s|^)' + re.escape(term) + r'(?:\s|$)'
                                    datf_sub = datf_sub1[datf_sub1['DISEASE/TRAIT'].str.contains(term_pattern, flags=re.IGNORECASE, na=False)]
                                    if not datf_sub.empty:
                                        for _, row in datf_sub.iterrows():
                                            gwas_text = f"SNP:{row['SNPS']}, P value: {row['P-VALUE']}, Disease/trait: {row['DISEASE/TRAIT']}, Mapped trait: {row['MAPPED_TRAIT']}"
                                            gwas_sents_for_node.append({'pmid': row['PUBMEDID'], 'text': gwas_text, 'category': keyword_node})
                        if gwas_sents_for_node:
                            gwas_by_keyword = {}
                            for s in gwas_sents_for_node:
                                kw = s['category']
                                if kw not in gwas_by_keyword: gwas_by_keyword[kw] = []
                                gwas_by_keyword[kw].append(s)
                            for keyword, sentences in sorted(gwas_by_keyword.items()):
                                gwas_formatted_sentences += f"\n\n## Keyword: {keyword} (Category: GWAS)\n"
                                unique_sentences = {f"{s['pmid']}_{s['text']}": s for s in sentences}
                                for sent_obj in unique_sentences.values(): gwas_formatted_sentences += f"- {sent_obj['text']} (PMID: {sent_obj['pmid']})\n"
                except FileNotFoundError: print("Warning: ./utility/gwas_used.csv not found.")
                except Exception as e: print(f"Error processing GWAS data in /synonyms fallback: {e}")

            formatted_sentences = pubmed_formatted_sentences + gwas_formatted_sentences

        # --- Part 4: Assemble final prompt ---
        if not formatted_sentences.strip():
            formatted_sentences = "No relevant sentences were found in the literature for this gene."

        prompt_string = GENECUP_PROMPT_TEMPLATE.replace("{{gene}}", node)
        prompt_string += formatted_sentences

        return render_template('genenames.html', case=case, gene=node.upper(), synonym_list=synonym_list, synonym_list_str=synonym_list_str, prompt=prompt_string,version=version())

    except KeyError:
        case = 2
        return render_template('genenames.html', gene=node, case=case,version=version())
    except Exception as e:
        print(f"An unexpected error occurred in /synonyms for node {node}: {e}")
        return f"An error occurred while processing your request for {node}.", 500


# Generate a page that lists all the top 150 addiction genes with links to cytoscape graph.
@app.route("/allTopGenes")
def top150genes():
    return render_template("topAddictionGene.html",no_footer=True,version=version())


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='GeneCup server')
    parser.add_argument('-p', '--port', type=int, default=4200, help='port number (default: 4200)')
    parser.add_argument('-d', '--debug', action='store_true', help='enable debug mode')
    args = parser.parse_args()
    print("GeneCup server starting...")
    print(f"  EDIRECT_PUBMED_MASTER={os.environ.get('EDIRECT_PUBMED_MASTER', '(not set)')}")
    print(f"  GEMINI_API_KEY={'set' if os.environ.get('GEMINI_API_KEY') else '(not set)'}")
    print(f"  NLTK_DATA={os.environ.get('NLTK_DATA', '(not set)')}")
    print(f"  GENECUP_DATADIR={os.environ.get('GENECUP_DATADIR', '(not set, default: ./)')}")
    app.run(debug=args.debug, host='0.0.0.0', port=args.port)
