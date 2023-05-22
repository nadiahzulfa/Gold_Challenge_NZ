#Panggil-panggil Modul/Package yang diperlukan

import pandas as pd
import re
from flask import Flask,jsonify
from flask import request

from flasgger import Swagger,LazyString,LazyJSONEncoder
from flasgger import swag_from

import sqlite3
import json

app= Flask(__name__)
app.json_encoder=LazyJSONEncoder

# Set Judul Halaman 
swagger_template=dict(
    info={
        'title':LazyString(lambda:'API Documentation - Gold Challenge NZ'),
        'version':LazyString(lambda:'1.0.0'),
        'description':LazyString(lambda:'Dokumentasi API-Gold Challenge'),
    },
    host=LazyString(lambda:request.host)
)

#Routing
swagger_config={
    'headers':[],
    'specs':[
        {
            'endpoint':'docs',
            'route':'/docs.json',
        }
    ],
    'static_url_path':'/flasgger_static',
    'swagger_ui':True,
    'specs_route':'/docs/'
}

# Menggabungkan Template dan konfigurasi Swagger
swagger=Swagger(app,template=swagger_template,config=swagger_config)

#Membaca semua dataset yang ada
alay_dict=pd.read_csv("new_kamusalay.csv",encoding='latin1',header=None)
alay_dict=alay_dict.rename(columns={0:'Original',1:'Baku'})

abusive_dict=pd.read_csv("abusive.csv",encoding='latin1')
abusive_dict['Kata_Sensor']="***disensor***" #Inisiasi kata ganti untuk kata-kata yang kasar dengan kata "disensor"

#print(kasar_dict)

alay_dict_map = dict(zip(alay_dict['Original'], alay_dict['Baku']))
abusive_dict_map = dict(zip(abusive_dict['ABUSIVE'],abusive_dict['Kata_Sensor']))


@swag_from("docs/hello_world.yml",methods=['GET'])
@app.route('/',methods=['GET'])
def hello_world():
    json_response={
        'status_code':200,
        'description':"Menyapa",
        'data':'Hello World',
    }
    response_data=jsonify(json_response)
    return response_data


@swag_from("docs/text_processing.yml")
@app.route('/text-processing',methods=['POST'])
def text_processing():
    global text
    conn=sqlite3.connect('DB_Gold_Challange.db')
    cursor=conn.cursor()
    text=request.form.get('text')
    text1=text
    text1=str(text1)
    text2=preprocess(text1)
    text2=str(text2)
    json_response={

        'description':'Tampilkan Teks',    
        'data_before_cleansing':text1,
        'data_after_cleansing':text2,
        'status_code':200,
    }
    response_data=jsonify(json_response)
    conn.execute("INSERT INTO Proses_Kata (id,teks_asli,teks_setelah_cleansing) VALUES(NULL,?,?)",(text1,text2))
    conn.commit()
    conn.close()
    return response_data

#@swag_from("docs/show_text.yml")
#@app.route('/show-text',methods=['GET'])
#def show_text():
   # json_response={

       # 'description':'Teks Sebelum Cleansing dan Teks Setelah Cleansing',
       # 'data_after_cleansing':preprocess(text),
        #'data_before_cleansing':text,
        #'status_code':200,
   # }
   # response_data=jsonify(json_response)
   # return response_data

@swag_from('docs/file_processing.yml')
@app.route('/file_processing', methods=['POST'])
def file_processing():
    
    file = request.files.getlist('file')[0]
    df = pd.read_csv(file,encoding='latin-1')
    texts_kotor=df['Tweet']
    texts_kotor=texts_kotor.to_list()
    df['Tweet']=df['Tweet'].apply(preprocess)

    texts=df['Tweet'].to_list()

    json_response={
        'status_code':200,
        'description':'Tweet Yang Sudah Di Cleansing',
        'data_before_cleansing':texts_kotor,
        'data_after_cleansing':texts
    }

    kumpulan_kata=list(zip(texts_kotor,texts))
    response_data=jsonify(json_response)

    conn=sqlite3.connect('DB_Glod_Challenge.db')
    cursor=conn.cursor()
    cursor.executemany("INSERT INTO Proses_Kata (id,teks_asli, teks_setelah_cleansing) VALUES (NULL,?, ?)",kumpulan_kata)
    
    conn.commit()
    conn.close()
    
    return response_data
    

def normalize_alay(text):
    return ' '.join([alay_dict_map[word] if word in alay_dict_map else word for word in text.split(' ')])


def sensor_kata_abusive(text):
    return ' '.join([abusive_dict_map[word] if word in abusive_dict_map else word for word in text.split(' ')])


def preprocess(TeksProses):

  
    #Lowercasing- Membuat semua huruf menjadi huruf kecil 
    text = TeksProses.lower()

    #menghilangkan karakter non-alfa numerik
    text = re.sub('[^0-9a-zA-Z]+',' ',text)

    # menghilangkan karakter yang tidak penting
    text=re.sub('\n',' ',text) #Menghilangkan new line pada data
    text=re.sub('rt',' ',text) #Menghilangkan kata-kata retweet 
    text=re.sub('user',' ',text) #Menghilangkan kata-kata user
    text=re.sub('((www\.[^\s]+)|(https?://[^\s]+)|(http?://[^\s]+))',' ',text) #Menghilangkan  URL
    text=re.sub(' +',' ',text) #Menghilangkan ekstra spasi

    # membuat map terhadap kata-kata "alay" dan mengubah nya menjadi kata yang baku
    text=normalize_alay(text)

    #Sensor kata kasar dengan kata "***disensor***"
    text=sensor_kata_abusive(text)
    return text


#untuk EDA
def program():
    df_data = pd.read_csv("data.csv",encoding='latin1')
    print("Jumlah Data Terduplikasi Saat Ini : " + str(df_data.duplicated().sum()))
    df_data=df_data.drop_duplicates()
    print("Jumlah Data Terduplikasi Sekarang Adalah : "+str(df_data.duplicated().sum()))

    print("Jumlah Elemen NaN Pada Data : "+str(df_data.isna().sum()))
    
    df_data['Tweet']=df_data['Tweet'].apply(preprocess)
    print(df_data)

    df_data.to_csv("Tweet yang telah di cleansing dan di sensor.csv")

    conn=sqlite3.connect('DB_Gold_Challange.db')
    cursor=conn.cursor()
    try:
        cursor.execute('''CREATE TABLE Proses_Kata (id INTEGER PRIMARY KEY AUTOINCREMENT, teks_asli varchar(255), teks_setelah_cleansing varchar(255))''')
        print("Tabel Berhasil Dibuat")
    except sqlite3.OperationalError:
        print("Tabel Telah Dibuat")
    conn.commit()
    conn.close()
    

if __name__=="__main__":
    program()
    app.run()