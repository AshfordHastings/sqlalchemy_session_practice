from sqlalchemy import create_engine, Column, Integer, String, DECIMAL, Date, BigInteger, MetaData
from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

engine = create_engine('postgresql://postgres:password@localhost/flashcard_db')

Base = declarative_base()
# metadata = Metadata()

class Movie(Base):
    __tablename__ = 'movie'
    __table_args__ = {'schema': 'practice'}  # Specify the schema

    movie_id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(1000), default=None)
    budget = Column(Integer, default=None)
    homepage = Column(String(1000), default=None)
    overview = Column(String(1000), default=None)
    popularity = Column(DECIMAL(12, 6), default=None)
    release_date = Column(Date, default=None)
    revenue = Column(BigInteger, default=None)
    runtime = Column(Integer, default=None)
    movie_status = Column(String(50), default=None)
    tagline = Column(String(1000), default=None)
    vote_average = Column(DECIMAL(4, 2), default=None)
    vote_count = Column(Integer, default=None)

Base.metadata.create_all(engine) # Metadata holds all the information about the tables and columns - generated from subclasses of declarative_base
Session = sessionmaker(bind=engine)