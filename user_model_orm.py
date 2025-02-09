from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship, DeclarativeBase
from sqlalchemy.types import String, Date
from typing import List

import datetime as dt

class Base(DeclarativeBase):
    pass

###################
# Create the models
###################

class User(Base):
    __tablename__ = 'user_account'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(30))
    fullname: Mapped[str] = mapped_column(String)
    surname: Mapped[str] = mapped_column(String(50))

    addresses: Mapped[List["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"User(id={self.id!r}, name={self.name!r}, fullname={self.fullname!r})"

class Address(Base):
    __tablename__ = 'address'

    id: Mapped[int] = mapped_column(primary_key=True)
    email_address: Mapped[str]
    user_id: Mapped[int] = mapped_column(ForeignKey("user_account.id"))

    user: Mapped["User"] = relationship(back_populates='addresses')

    def __repr__(self):
        return f"Address(id={self.id!r}, email_address={self.email_address!r})"


class Datatable(Base):
    __tablename__ = 'datatable'

    id: Mapped[int] = mapped_column(primary_key=True)
    datadate: Mapped[dt.date] = mapped_column(Date)
    datacomment: Mapped[str] = mapped_column(String(255))

    def __repr__(self):
        return f'the value : {self.datadate}, {self.datacomment}'
