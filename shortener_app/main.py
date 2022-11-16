# shortener_app/main.py
# Note: run this file with "uvicorn shortener_app.main:app --reload"

from fastapi import FastAPI
import validators
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from . import schemas
from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from . import crud, models, schemas
from .database import SessionLocal, engine
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL
from .config import get_settings


class Raise(object):
    @classmethod
    def bad_request(cls, message):
        raise HTTPException(status_code=400, detail=message)

    @classmethod
    def not_found(cls, request):
        cls.bad_request(f"URL '{request.url}' doesn't exist")


app = FastAPI()
models.Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_admin_info(db_url: models.URL) -> schemas.URLInfo:
    base_url = URL(get_settings().base_url)
    admin_endpoint = app.url_path_for(
        "administration info", secret_key=db_url.secret_key)
    db_url.url = str(base_url.replace(path=db_url.key))
    db_url.admin_url = str(base_url.replace(path=admin_endpoint))
    return db_url


@app.get("/", response_class=HTMLResponse)
def read_root():
    return "This is the url-shortener API for <a href='https://beb.mzecheru.com/site/'>beb.mzecheru.com</a><br><br>Visit <a href='https://beb.mzecheru.com/site/register'>https://beb.mzecheru.com/site/register</a> to interact with this API through the UI"


@app.post("/url", response_model=schemas.URLInfo)
def create_url(url: schemas.URLBase, custom: str = None, db: Session = Depends(get_db)):
    if not validators.url(url.target_url):
        Raise.bad_request(message="Your provided URL is not valid")

    if custom and len(custom) < 3:
        Raise.bad_request(
            message="Custom URL must be at least 3 characters long")

    db_url = crud.create_db_url(db, url, custom)
    if type(db_url) == Exception:
        Raise.bad_request(message=str(db_url))
    return get_admin_info(db_url)


@app.get("/{url_key}")
def forward_to_target_url(url_key: str, request: Request, db: Session = Depends(get_db)):
    # Get the url
    if db_url := crud.get_db_url_by_key(db, url_key):
        crud.update_db_clicks(db, db_url)
        return RedirectResponse(db_url.target_url)
    else:
        # If the url doesn't exist
        Raise.not_found(request)


@app.get("/admin/{secret_key}", name="administration info", response_model=schemas.URLInfo)
def get_url_info(secret_key: str, request: Request, db: Session = Depends(get_db)):
    if db_url := crud.get_db_url_by_secret(db, secret_key):
        db_url.url = db_url.key
        db_url.admin_url = db_url.secret_key
        return get_admin_info(db_url)
    else:
        Raise.not_found(request)


@app.delete("/admin/{secret_key}")
def delete_url(secret_key: str, request: Request, db: Session = Depends(get_db)):
    if db_url := crud.deactivate_url(db, secret_key):
        message = f"Successfully deleted shortened URL for '{db_url.target_url}'"
        return {"detail": message}
    else:
        Raise.not_found(request)
