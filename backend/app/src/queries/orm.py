from src.models import Base, IPAddress, WhoisInfo
from src.database import session_factory, sync_engine
from sqlalchemy import select, inspect
from sqlalchemy.exc import IntegrityError
from typing import Optional, Dict

class SyncOrm:
    @staticmethod
    def create_tables():
        """Создание и сброс всех таблиц в базе данных."""
        # Base.metadata.drop_all(sync_engine)
        table_names = inspect(sync_engine).get_table_names()
        if not table_names:
            Base.metadata.create_all(sync_engine)

    @staticmethod
    def insert_ip_address(ip: str) -> Optional[IPAddress]:
        """
        Добавляет новый IP-адрес в базу данных.
        
        :param ip: IP-адрес для добавления
        :return: Объект IPAddress или None при ошибке
        """
        with session_factory() as session:
            try:
                # Проверяем, существует ли уже такой IP
                existing_ip = session.execute(
                    select(IPAddress).where(IPAddress.ip == ip)
                ).scalar_one_or_none()
                
                if existing_ip:
                    print(f"IP-адрес {ip} уже существует в базе")
                    return existing_ip
                
                new_ip = IPAddress(ip=ip)
                session.add(new_ip)
                session.commit()
                session.refresh(new_ip)
                print(f"IP-адрес {ip} успешно добавлен")
                return new_ip
            except IntegrityError:
                session.rollback()
                print(f"Ошибка целостности при добавлении IP {ip}")
                return None
            except Exception as e:
                session.rollback()
                print(f"Ошибка при добавлении IP {ip}: {e}")
                return None

    @staticmethod
    def add_whois_info(
        ip: str,
        asn: str,
        name: str,
        country: str
    ) -> Optional[WhoisInfo]:
        """
        Добавляет или обновляет WHOIS информацию для IP-адреса.
        
        :param ip: IP-адрес
        :param asn: Номер AS
        :param name: Название сети
        :param country: Код страны (2 символа)
        :return: Объект WhoisInfo или None при ошибке
        """
        with session_factory() as session:
            try:
                # Находим IP-адрес
                ip_address = session.execute(
                    select(IPAddress).where(IPAddress.ip == ip)
                ).scalar_one_or_none()
                
                if not ip_address:
                    print(f"IP-адрес {ip} не найден")
                    return None
                
                # Проверяем существующую WHOIS информацию
                whois_info = session.execute(
                    select(WhoisInfo).where(WhoisInfo.ip_address_id == ip_address.id)
                ).scalar_one_or_none()
                
                if whois_info:
                    # Обновляем существующую запись
                    whois_info.asn = asn
                    whois_info.name = name
                    whois_info.country = country
                else:
                    # Создаем новую запись
                    whois_info = WhoisInfo(
                        ip_address_id=ip_address.id,
                        asn=asn,
                        name=name,
                        country=country
                    )
                    session.add(whois_info)
                
                session.commit()
                session.refresh(whois_info)
                print(f"WHOIS информация для {ip} успешно сохранена")
                return whois_info
            except IntegrityError:
                session.rollback()
                print(f"Ошибка целостности при добавлении WHOIS для {ip}")
                return None
            except Exception as e:
                session.rollback()
                print(f"Ошибка при добавлении WHOIS для {ip}: {e}")
                return None