from contextlib import asynccontextmanager
import os

from fastapi import Depends, FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import Integer, String, create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker


def normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return raw_url.replace("postgres://", "postgresql+psycopg://", 1)
    if raw_url.startswith("postgresql://"):
        return raw_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return raw_url


DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable is required")

DATABASE_URL = normalize_database_url(DATABASE_URL)


class Base(DeclarativeBase):
    pass


class BookRecord(Base):
    __tablename__ = "book"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    published_year: Mapped[int] = mapped_column(Integer, nullable=False)


is_sqlite = DATABASE_URL.startswith("sqlite")
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=not is_sqlite,
    connect_args={"check_same_thread": False} if is_sqlite else {},
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        raise RuntimeError(
            "Database connection failed. Check DATABASE_URL and confirm the Render PostgreSQL host is reachable."
        ) from exc
    yield


app = FastAPI(title="Books API", lifespan=lifespan)


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    published_year: int = Field(..., ge=0, le=9999)


class BookUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(..., min_length=1, max_length=100)
    published_year: int = Field(..., ge=0, le=9999)


class Book(BaseModel):
    id: int
    title: str
    author: str
    published_year: int

    model_config = {"from_attributes": True}


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "Books API with Render PostgreSQL is running"}


@app.get("/books", response_model=list[Book])
def list_books(db: Session = Depends(get_db)) -> list[BookRecord]:
    return db.query(BookRecord).order_by(BookRecord.id).all()


@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, db: Session = Depends(get_db)) -> BookRecord:
    book = BookRecord(**payload.model_dump())
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@app.get("/books/{book_id}", response_model=Book)
def get_book(book_id: int, db: Session = Depends(get_db)) -> BookRecord:
    book = db.get(BookRecord, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@app.put("/books/{book_id}", response_model=Book)
def update_book(book_id: int, payload: BookUpdate, db: Session = Depends(get_db)) -> BookRecord:
    book = db.get(BookRecord, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    for field, value in payload.model_dump().items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, db: Session = Depends(get_db)) -> Response:
    book = db.get(BookRecord, book_id)
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")

    db.delete(book)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
