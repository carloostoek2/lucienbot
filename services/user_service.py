"""
Servicio de Usuarios - Lucien Bot

Gestiona la lógica de usuarios y administradores.
"""
from typing import Optional, List
from sqlalchemy.orm import Session
from models.models import User, UserRole
from models.database import SessionLocal


class UserService:
    """Servicio para gestión de usuarios"""
    
    def __init__(self, db: Session = None):
        self.db = db or SessionLocal()
    
    def create_user(self, telegram_id: int, username: str = None,
                    first_name: str = None, last_name: str = None,
                    role: UserRole = UserRole.USER) -> User:
        """Crea un nuevo usuario"""
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Obtiene un usuario por su ID de Telegram"""
        return self.db.query(User).filter(User.telegram_id == telegram_id).first()
    
    def get_or_create_user(self, telegram_id: int, username: str = None,
                           first_name: str = None, last_name: str = None) -> User:
        """Obtiene un usuario existente o lo crea si no existe"""
        user = self.get_user(telegram_id)
        if not user:
            user = self.create_user(telegram_id, username, first_name, last_name)
        else:
            # Actualizar información si ha cambiado
            updated = False
            if username and user.username != username:
                user.username = username
                updated = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                updated = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                updated = True
            if updated:
                self.db.commit()
        return user
    
    def get_all_users(self, active_only: bool = True) -> List[User]:
        """Obtiene todos los usuarios"""
        query = self.db.query(User)
        if active_only:
            query = query.filter(User.is_active == True)
        return query.all()
    
    def get_admins(self) -> List[User]:
        """Obtiene todos los administradores"""
        return self.db.query(User).filter(User.role == UserRole.ADMIN).all()
    
    def is_admin(self, telegram_id: int) -> bool:
        """Verifica si un usuario es administrador"""
        user = self.get_user(telegram_id)
        return user is not None and user.role == UserRole.ADMIN
    
    def set_admin(self, telegram_id: int) -> bool:
        """Establece un usuario como administrador"""
        user = self.get_user(telegram_id)
        if user:
            user.role = UserRole.ADMIN
            self.db.commit()
            return True
        return False
    
    def remove_admin(self, telegram_id: int) -> bool:
        """Remueve privilegios de administrador"""
        user = self.get_user(telegram_id)
        if user:
            user.role = UserRole.USER
            self.db.commit()
            return True
        return False
    
    def deactivate_user(self, telegram_id: int) -> bool:
        """Desactiva un usuario"""
        user = self.get_user(telegram_id)
        if user:
            user.is_active = False
            self.db.commit()
            return True
        return False
    
    def close(self):
        """Cierra la sesión de base de datos"""
        if hasattr(self, 'db') and self.db:
            self.db.close()
            self.db = None

    def __del__(self):
        """Cierra la sesión de base de datos"""
        self.close()
