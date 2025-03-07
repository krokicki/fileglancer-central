
from fileglancer_central.settings import get_settings
from loguru import logger
settings = get_settings()

from sqlalchemy import create_engine, Column, String, Integer, DateTime
from sqlalchemy.orm import sessionmaker, declarative_base
from datetime import datetime

Base = declarative_base()

class FileSharePathDB(Base):
    __tablename__ = 'file_share_paths'
    id = Column(Integer, primary_key=True, autoincrement=True)
    lab = Column(String)
    group = Column(String)
    storage = Column(String)
    canonical_path = Column(String, index=True, unique=True)
    mac_path = Column(String)
    windows_path = Column(String)
    linux_path = Column(String)
    

class LastRefreshDB(Base):
    __tablename__ = 'last_refresh'
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_last_updated = Column(DateTime, nullable=False)
    db_last_updated = Column(DateTime, nullable=False)


def get_db_session():
    """Create and return a database session"""
    engine = create_engine(settings.db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    Base.metadata.create_all(engine)
    return session


def get_all_paths(session):
    """Get all file share paths from the database"""
    return session.query(FileSharePathDB).all()


def get_last_refresh(session):
    """Get the last refresh time from the database"""
    return session.query(LastRefreshDB).first()


def get_canonical_path(row):
    """Get the canonical path from the row"""
    return row['linux_path']


def update_file_share_paths(session, table, table_last_updated, max_paths_to_delete=2):
    """Update database with new file share paths"""
    # Get all existing linux_paths from database
    existing_paths = {path[0] for path in session.query(FileSharePathDB.canonical_path).all()}
    new_paths = set()
    num_existing = 0
    num_new = 0

    # Update or insert records
    for _, row in table.iterrows():
        canonical_path = get_canonical_path(row)
        new_paths.add(canonical_path)
        
        # Check if path exists
        existing_record = session.query(FileSharePathDB).filter_by(canonical_path=canonical_path).first()
        
        if existing_record:
            # Update existing record
            existing_record.lab = row['lab']
            existing_record.storage = row['storage'] 
            existing_record.mac_path = row['mac_path']
            existing_record.windows_path = row['windows_path']
            existing_record.linux_path = row['linux_path']
            existing_record.group = row['group']
            num_existing += 1

        else:
            # Create new record
            new_record = FileSharePathDB(
                lab=row['lab'],
                storage=row['storage'],
                canonical_path=canonical_path,
                mac_path=row['mac_path'],
                windows_path=row['windows_path'],
                linux_path=row['linux_path'],
                group=row['group']
            )
            session.add(new_record)
            num_new += 1

    logger.debug(f"Updated {num_existing} file share paths, added {num_new} file share paths")

    # Delete records that no longer exist in the wiki
    paths_to_delete = existing_paths - new_paths
    if paths_to_delete:
        if len(paths_to_delete) > max_paths_to_delete:
            logger.warning(f"Cannot delete {len(paths_to_delete)} defunct file share paths from the database, only {max_paths_to_delete} are allowed")
        else:
            logger.debug(f"Deleting {len(paths_to_delete)} defunct file share paths from the database")
            session.query(FileSharePathDB).filter(FileSharePathDB.linux_path.in_(paths_to_delete)).delete(synchronize_session='fetch')

    # Update last refresh time
    session.query(LastRefreshDB).delete()
    session.add(LastRefreshDB(source_last_updated=table_last_updated, db_last_updated=datetime.now()))

    session.commit()