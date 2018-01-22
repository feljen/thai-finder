import os
#import datetime

from flask import Flask, render_template

from flask_sqlalchemy import SQLAlchemy
from flask_rqify import init_rqify
from flask_rq import job
import pandas as pd
from sqlalchemy import *


app = Flask(__name__)
init_rqify(app)
engine = create_engine(os.environ['DATABASE_URL'])
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['DATABASE_URL']
db = SQLAlchemy(app)
metadata = MetaData()

restaurant = Table('restaurant', metadata,
    Column('id', Integer, primary_key=True),
    Column('name', String(100)),
    Column('boro', String(100)),
    Column('address', String(100)),
    Column('zipcode', String(100)),
    Column('phone', String(100))
)

grade = Table('grade', metadata,
    Column('id', Integer, primary_key=True),
    Column('restaurant_id', Integer, ForeignKey('restaurant.id'), nullable=False),
    Column('score', Integer),
    Column('date', Date),
    Column('grade', String(1))
)

metadata.create_all(engine)


@job
def process_csv():
    url = 'https://nycopendata.socrata.com/api/views/xx67-kt59/rows.csv?accessType=DOWNLOAD'
    data = pd.read_csv(url)
    acceptable_grades = ['A', 'B']
    thai_restaurants = data.loc[data["CUISINE DESCRIPTION"] == 'Thai']
    df = thai_restaurants.loc[data["GRADE"].isin(acceptable_grades)]
    df['address'] = df['BUILDING'] + df['STREET']
    df2 = df[df.columns.difference(['CUISINE DESCRIPTION', 'BUILDING', 'STREET', 'ACTION', 'VIOLATION CODE', 'VIOLATION DESCRIPTION', 'CRITICAL FLAG', 'SCORE', 'GRADE', 'INSPECTION DATE', 'GRADE DATE', 'RECORD DATE', 'INSPECTION TYPE'])]
    df2 = df2.rename(columns={'CAMIS':'id', 'DBA': 'name', 'BORO':'boro', 'PHONE':'phone', 'ZIPCODE': 'zipcode'})
    df2['id'] = df2['id'].unique()
    df2.to_sql(con=engine, name='restaurant', if_exists='append', index=False)
    df3 = df[df.columns.difference(['address', 'DBA', 'BORO', 'BUILDING', 'STREET', 'ZIPCODE', 'PHONE', 'CUISINE DESCRIPTION', 'CRITICAL FLAG', 'INSPECTION DATE', 'RECORD DATE', 'INSPECTION TYPE'])]
    df3 = df3.rename(columns={'CAMIS': 'restaurant_id', 'SCORE': 'score', 'GRADE DATE': 'date', 'GRADE': 'grade'})
    df3.to_sql(con=engine, name='grade', if_exists='append', dtype={'date': Date})


@app.route("/")
def get_restaurants():
    rest_qs = engine.execute("""SELECT * FROM restaurant ORDER BY "SCORE" asc limit 10""").fetchall()
    data_dict = {}
    for rest in rest_qs:
        if rest['BORO'] in data_dict:
            data_dict[rest['BORO']].append(rest['DBA'])
        else:
            data_dict[rest['BORO']] = [rest['DBA']]
    return render_template('layout.html', data=data_dict)


if __name__ == "__main__":
    app.run(debug=True)
