# shortener_app/crud.py

from sqlalchemy.orm import Session
from . import models, schemas
import secrets


def get_db_url_by_key(db: Session, url_key: str) -> models.URL:
    return (
        db.query(models.URL)
        .filter(models.URL.key == url_key, models.URL.is_active)
        .first()
    )


def get_db_url_by_secret(db: Session, secret: str) -> models.URL:
    return (
        db.query(models.URL)
        .filter(models.URL.secret_key == secret, models.URL.is_active)
        .first()
    )


class Create(object):
    chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    @classmethod
    def _key(cls) -> str:
        return "".join(secrets.choice(cls.chars) for _ in range(6))

    @classmethod
    def key(cls, db) -> str:
        key = cls._key()
        while get_db_url_by_key(db, key):
            key = cls._key()
        return key

    @classmethod
    def _section_of_secret(cls) -> str:
        chars = cls.chars + cls.chars.lower()
        return "".join(secrets.choice(chars) for _ in range(10))

    @classmethod
    def _secret(cls, key) -> str:
        return f"{key}-{cls._section_of_secret()}-{cls._section_of_secret()}-{cls._section_of_secret()}"

    @classmethod
    def secret(cls, db, key) -> str:
        secret = cls._secret(key)
        while get_db_url_by_secret(db, secret):
            secret = cls._secret()
        return secret


def create_db_url(db: Session, url: schemas.URLBase, custom: str) -> models.URL:
    if custom and (custom in [ "site", "docs" ] or get_db_url_by_key(db, custom)):
        return Exception("Custom URL already exists")

    key = custom or Create.key(db)
    secret = Create.secret(db, key)

    db_url = models.URL(
        target_url=url.target_url,
        key=key,
        secret_key=secret
    )

    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    db_url.url = key
    db_url.admin_url = secret
    return db_url


def update_db_clicks(db: Session, db_url: schemas.URL) -> models.URL:
    db_url.clicks += 1
    db.commit()
    db.refresh(db_url)
    return db_url


def deactivate_url(db: Session, secret_key: str) -> models.URL:
    db_url = get_db_url_by_secret(db, secret_key)
    if db_url:
        db_url.is_active = False
        db.commit()
        db.refresh(db_url)
    return db_url
