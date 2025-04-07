from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from src.database import Base

class IPAddress(Base):
    __tablename__ = 'ip_addresses'
    
    id = Column(Integer, primary_key=True)
    ip = Column(String(45), index=True)

    whois_info = relationship("WhoisInfo", back_populates="ip_address", uselist=False)

class WhoisInfo(Base):
    __tablename__ = 'whois_info'
    
    id = Column(Integer, primary_key=True)
    ip_address_id = Column(Integer, ForeignKey('ip_addresses.id'))
    asn = Column(String(50))
    name = Column(String(255))
    country = Column(String(2))
    
    ip_address = relationship("IPAddress", back_populates="whois_info")