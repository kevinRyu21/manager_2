"""
얼굴 인식 데이터베이스 관리 모듈

학습된 얼굴 특징을 저장하고 관리합니다.
"""

import sqlite3
import os
import json
import numpy as np
from datetime import datetime
from typing import List, Tuple, Optional, Dict
import pickle

from ..utils.helpers import get_data_dir


class FaceDatabase:
    """얼굴 인식 데이터베이스 관리 클래스"""

    def __init__(self, db_path: str = None):
        """
        초기화

        Args:
            db_path: 데이터베이스 파일 경로 (None이면 기본 경로 사용)
        """
        if db_path is None:
            # 기본 경로: 프로젝트 루트의 face_db 디렉토리
            # get_data_dir()는 PyInstaller 호환 경로를 반환
            db_dir = get_data_dir('face_db')
            db_path = os.path.join(db_dir, 'faces.db')

        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 얼굴 정보 테이블
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                employee_id TEXT,
                department TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                photo_path TEXT,
                is_active INTEGER DEFAULT 1
            )
        ''')
        
        # 얼굴 특징 인코딩 테이블 (각 얼굴당 여러 인코딩 저장 가능)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_encodings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                face_id INTEGER NOT NULL,
                encoding BLOB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (face_id) REFERENCES faces(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_face(self, name: str, encoding: np.ndarray, employee_id: str = None, 
                  department: str = None, photo_path: str = None) -> int:
        """
        얼굴 정보 및 인코딩 추가
        
        Args:
            name: 이름
            encoding: 얼굴 인코딩 (128차원 벡터)
            employee_id: 사원번호 (선택)
            department: 부서 (선택)
            photo_path: 원본 사진 경로 (선택)
        
        Returns:
            추가된 얼굴 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 기존 얼굴이 있는지 확인 (이름으로)
        cursor.execute('SELECT id FROM faces WHERE name = ? AND is_active = 1', (name,))
        existing = cursor.fetchone()
        
        if existing:
            face_id = existing[0]
            # 기존 얼굴에 인코딩 추가
            cursor.execute('''
                UPDATE faces SET updated_at = CURRENT_TIMESTAMP,
                                photo_path = COALESCE(?, photo_path)
                WHERE id = ?
            ''', (photo_path, face_id))
        else:
            # 새 얼굴 추가
            cursor.execute('''
                INSERT INTO faces (name, employee_id, department, photo_path)
                VALUES (?, ?, ?, ?)
            ''', (name, employee_id, department, photo_path))
            face_id = cursor.lastrowid
        
        # 얼굴 인코딩 저장 (BLOB으로 변환)
        encoding_bytes = pickle.dumps(encoding)
        cursor.execute('''
            INSERT INTO face_encodings (face_id, encoding)
            VALUES (?, ?)
        ''', (face_id, encoding_bytes))
        
        conn.commit()
        conn.close()
        return face_id
    
    def get_all_faces(self) -> List[Dict]:
        """
        모든 활성 얼굴 정보 조회
        
        Returns:
            얼굴 정보 리스트
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, employee_id, department, created_at, updated_at, photo_path
            FROM faces
            WHERE is_active = 1
            ORDER BY name
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        faces = []
        for row in rows:
            faces.append({
                'id': row[0],
                'name': row[1],
                'employee_id': row[2],
                'department': row[3],
                'created_at': row[4],
                'updated_at': row[5],
                'photo_path': row[6]
            })
        
        return faces
    
    def get_face_encodings(self, face_id: int = None) -> List[np.ndarray]:
        """
        얼굴 인코딩 조회
        
        Args:
            face_id: 특정 얼굴 ID (None이면 모든 활성 얼굴의 인코딩)
        
        Returns:
            얼굴 인코딩 리스트
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if face_id:
            cursor.execute('''
                SELECT encoding FROM face_encodings
                WHERE face_id = ?
            ''', (face_id,))
        else:
            # 모든 활성 얼굴의 인코딩
            cursor.execute('''
                SELECT fe.encoding FROM face_encodings fe
                INNER JOIN faces f ON fe.face_id = f.id
                WHERE f.is_active = 1
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        encodings = []
        for row in rows:
            encoding = pickle.loads(row[0])
            encodings.append(encoding)
        
        return encodings
    
    def get_face_info_by_id(self, face_id: int) -> Optional[Dict]:
        """
        얼굴 ID로 정보 조회
        
        Args:
            face_id: 얼굴 ID
        
        Returns:
            얼굴 정보 또는 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, name, employee_id, department, created_at, updated_at, photo_path
            FROM faces
            WHERE id = ? AND is_active = 1
        ''', (face_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'name': row[1],
                'employee_id': row[2],
                'department': row[3],
                'created_at': row[4],
                'updated_at': row[5],
                'photo_path': row[6]
            }
        return None
    
    def delete_face(self, face_id: int):
        """
        얼굴 정보 삭제 (소프트 삭제)
        
        Args:
            face_id: 얼굴 ID
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE faces SET is_active = 0, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (face_id,))
        
        conn.commit()
        conn.close()
    
    def recognize_face(self, encoding: np.ndarray, tolerance: float = 0.6) -> Optional[Tuple[int, str, float]]:
        """
        얼굴 인식
        
        Args:
            encoding: 비교할 얼굴 인코딩
            tolerance: 인식 허용 오차 (기본값 0.6, 낮을수록 엄격)
        
        Returns:
            (face_id, name, distance) 또는 None
        """
        # 모든 활성 얼굴의 인코딩 가져오기
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fe.face_id, fe.encoding, f.name
            FROM face_encodings fe
            INNER JOIN faces f ON fe.face_id = f.id
            WHERE f.is_active = 1
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return None
        
        # 거리 계산
        best_match = None
        best_distance = float('inf')
        
        for row in rows:
            face_id = row[0]
            stored_encoding = pickle.loads(row[1])
            name = row[2]
            
            # 유클리드 거리 계산
            distance = np.linalg.norm(encoding - stored_encoding)
            
            if distance < best_distance:
                best_distance = distance
                best_match = (face_id, name, distance)
        
        # 허용 오차 내에 있으면 반환
        if best_match and best_match[2] <= tolerance:
            return best_match

        return None

    def recognize_face_insightface(self, embedding: np.ndarray, tolerance: float = 0.4) -> Optional[Tuple[int, str, float]]:
        """
        InsightFace 임베딩으로 얼굴 인식

        InsightFace는 512차원 임베딩을 생성하며, 코사인 유사도를 사용합니다.

        Args:
            embedding: InsightFace 512차원 임베딩 벡터
            tolerance: 인식 허용 오차 (기본값 0.4, 코사인 거리 기준)

        Returns:
            (face_id, name, distance) 또는 None
        """
        # 모든 활성 얼굴의 인코딩 가져오기
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT fe.face_id, fe.encoding, f.name
            FROM face_encodings fe
            INNER JOIN faces f ON fe.face_id = f.id
            WHERE f.is_active = 1
        ''')

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return None

        # 입력 임베딩 정규화
        embedding_norm = embedding / np.linalg.norm(embedding)

        # 거리 계산
        best_match = None
        best_distance = float('inf')

        for row in rows:
            face_id = row[0]
            stored_embedding = pickle.loads(row[1])
            name = row[2]

            # 저장된 임베딩 정규화
            stored_norm = stored_embedding / np.linalg.norm(stored_embedding)

            # 코사인 거리 계산 (1 - 코사인 유사도)
            cosine_similarity = np.dot(embedding_norm, stored_norm)
            distance = 1 - cosine_similarity

            if distance < best_distance:
                best_distance = distance
                best_match = (face_id, name, distance)

        # 허용 오차 내에 있으면 반환
        if best_match and best_match[2] <= tolerance:
            return best_match

        return None

    def get_face_count(self) -> int:
        """활성 얼굴 개수 반환"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM faces WHERE is_active = 1')
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def update_face(self, face_id: int, name: str = None, employee_id: str = None,
                    department: str = None, photo_path: str = None) -> bool:
        """
        얼굴 정보 수정

        Args:
            face_id: 수정할 얼굴 ID
            name: 새 이름 (None이면 변경 안 함)
            employee_id: 새 사원번호 (None이면 변경 안 함)
            department: 새 부서 (None이면 변경 안 함)
            photo_path: 새 사진 경로 (None이면 변경 안 함)

        Returns:
            성공 여부
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 동적 업데이트 쿼리 생성
            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if employee_id is not None:
                updates.append("employee_id = ?")
                params.append(employee_id if employee_id else None)
            if department is not None:
                updates.append("department = ?")
                params.append(department if department else None)
            if photo_path is not None:
                updates.append("photo_path = ?")
                params.append(photo_path)

            if not updates:
                return False

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(face_id)

            query = f"UPDATE faces SET {', '.join(updates)} WHERE id = ? AND is_active = 1"
            cursor.execute(query, params)

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"[FaceDatabase] 얼굴 정보 수정 오류: {e}")
            return False
        finally:
            conn.close()

