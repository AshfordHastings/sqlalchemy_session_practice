import pytest, traceback
from sqlalchemy.exc import (
    IntegrityError,
    InvalidRequestError,
    PendingRollbackError
)
from sqlalchemy.orm.exc import (
    StaleDataError,
    DetachedInstanceError,
)

from sqlalchemy.orm import make_transient_to_detached

from model import Movie, Session 


def _remove_test_movie():
    with Session() as session:
        # test_movie = session.query(Movie) \
        #     .filter(Movie.title == "Test Movie") \
        #     .first()
        test_movie = session.query(Movie) \
            .filter(Movie.movie_id == 248) \
            .first()
        
        if test_movie:
            print("Deleting test movie")
            session.delete(test_movie)
            session.commit()

def test_query():
    with Session() as session:
        records = session.query(Movie) \
            .filter(Movie.title.startswith('A')) \
            .all()
        
    assert isinstance(records, list)
    assert len(records) >= 1


def test_read_from_session_after_close():
    """StaleDataError: Attempting to commit a transaction after the session is closed."""
    try:
        """This works fine!"""
        session = Session()

        new_movie = Movie(movie_id=248, title="Test Movie")
        session.add(new_movie)
        session.commit()

        session.close() # Session is closed

        #with pytest.raises(StaleDataError):
        new_movie.budget = 1000000
        session.commit()
    finally:
        _remove_test_movie()

    try:
        """Also works fine! Why does this work?"""
        session = Session()

        new_movie = Movie(movie_id=248,title="Test Movie")
        session.add(new_movie)
        session.commit()

        session.close() # Session is closed

        #with pytest.raises(StaleDataError):
        new_movie.budget = 1000000
        session.add(new_movie)
        session.commit()
    finally:
        _remove_test_movie()

    try:
        """DetachedInstanceError: Instance <Movie at 0x102f94b50> is not bound to a Session; attribute refresh operation cannot proceed"""
        """DetachedInstanceError: Occurs when you attempt to read from an object committed session after it has been closed"""
        session = Session()

        new_movie = Movie(movie_id=248,title="Test Movie")
        session.add(new_movie)
        session.commit()

        session.close() # Session is closed

        #with pytest.raises(StaleDataError):
        with pytest.raises(DetachedInstanceError):
            budget = new_movie.budget
    finally:
        _remove_test_movie()

    try:
        """Let's see if this occurs on sessions QUERIED..."""
        """DetachedInstanceError: Occurs when you attempt to read from an object committed session after it has been closed"""
        session = Session()

        new_movie = Movie(movie_id=248,title="Test Movie")
        session.add(new_movie)
        session.commit()

        session.close() # Session is closed

        session = Session() # Reopen session
        new_movie_queried_object = session.query(Movie).filter(Movie.movie_id == 248).first()

        session.close() # Session is closed

        budget = new_movie_queried_object.budget
        assert budget == None #Aha! Interesting! You can read from the object queried from the session after close, but NOT from the object committed to the session, after closure.

        # But can I write to it? 
        new_movie_queried_object.budget = 1000000 # This is fine - TODO: Try this with lazy loading

    finally:
        _remove_test_movie()


def test_query_session_before_commit():
    try:
        """ """
        session = Session()

        new_movie = Movie(movie_id=248, title="Test Movie")
        session.add(new_movie)
        
        # No commit!

        record = session.query(Movie).filter(Movie.movie_id == 248).first()
        assert record
        assert record.title == "Test Movie"

        # What about a new session?
        session2 = Session()
        record2 = session2.query(Movie).filter(Movie.movie_id == 248).first()
        assert record2 == None

        # Query requires a commit! 
        record.budget = 1000000
        session.commit()

        session3 = Session()
        record3 = session3.query(Movie).filter(Movie.movie_id == 248).first()
        assert record3
        assert record3.title == "Test Movie"
        assert record3.budget == 1000000

        # Try for dirty write
        record3.budget = 2000000
        session3.commit()

        assert record.budget == 2000000 # Automatic refresh? Interesting. I wonder if that only happens with same metadata object...

        # Dirty write: When two transactions are writing to the same record, and the last one wins, overwriting the first.
        # This also raises the potential for dirty reads, where a transaction reads a record before committing, and bases a write off of stale data (when a separate write happens after the commit).
        # I guess transactions are the way to mitigate this. 

        #with pytest.raises(StaleDataError):

    except Exception as e:
        print(e) 
        session.rollback()
        raise
    finally:
        _remove_test_movie()


def test_using_bad_session():
    try:
        session = Session()
        new_movie = Movie(movie_id=248, title="Test Movie")
        session.add(new_movie)
        session.commit()
        new_movie_dup = Movie(movie_id=248, title="Test Movie")
        session.add(new_movie_dup)
        with pytest.raises(IntegrityError):
            session.commit()

        new_movie.budget = 1000000

        with pytest.raises(PendingRollbackError):
            session.commit()

        session.rollback()

        session.commit() # SAWarning: Session's state has been changed on a non-active transaction - this state will be discarded.
        assert new_movie.budget == None

    except:
        session.rollback()
        raise
    finally:
        _remove_test_movie()

def test_adding_two_sessions():
    try:
        session1 = Session()
        session2 = Session()

        new_movie = Movie(movie_id=248, title="Test Movie")

        session1.add(new_movie)
        session1.commit()

        with pytest.raises(InvalidRequestError):
            session2.add(new_movie)
            session2.commit() # Breaks when you try to commit the same object to two different sessions

        # What about for queries?
        session1.close()
        session2.close()

        session1 = Session()
        session2 = Session()
        record1 = session1.query(Movie).filter(Movie.movie_id == 248).first()
        record1.budget = 1000000
        with pytest.raises(InvalidRequestError): # Also bad! 
            session2.add(record1)
            session2.commit()

        session1.close()
        session2.close()

        # Reverse the order...
        session1 = Session()
        session2 = Session()
        record1 = session1.query(Movie).filter(Movie.movie_id == 248).first()
        with pytest.raises(InvalidRequestError): # Also bad! 
            session2.add(record1)
            record1.budget = 1000000
            session2.commit()
        
        session1.close()
        session2.close()

        # DETATCHING FROM ONE SESSION AND ATTACHING TO ANOTHER.... 
        session1 = Session()
        session2 = Session()
        record1 = session1.query(Movie).filter(Movie.movie_id == 248).first()
        session1.expunge(record1)
        record1.budget = 2000000
        session2.add(record1)
        session2.commit()

        assert record1.budget == 2000000

        # with pytest.raises(InvalidRequestError): # Also bad! 
        #     session2.add(record1)
        #     record1.budget = 1000000
        #     session2.commit()
        
        session1.close()
        session2.close()

    except:
        session1.rollback()
        session2.rollback()
        raise
    finally:
        _remove_test_movie()



"""
Notes:
ISOLATION LEVELS

READ UNCOMMITTED: Allows dirty reads and dirty writes. Transactions can read uncommitted changes made by other transactions.
READ COMMITTED: Prevents dirty reads but allows non-repeatable reads and phantom reads. Transactions can only read committed changes.
REPEATABLE READ: Prevents dirty reads and non-repeatable reads but allows phantom reads. Transactions can see the same data if they re-read the same records.
SERIALIZABLE: Prevents dirty reads, non-repeatable reads, and phantom reads. Ensures complete isolation by making transactions appear to be executed sequentially.

DEFAULT for Postgres: READ COMMITTED
"""