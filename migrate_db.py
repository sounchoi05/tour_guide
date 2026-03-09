import sqlite3
import os

# app.py와 동일한 위치의 DB 파일 경로 설정
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'spain_trip.db')

def upgrade_db():
    print("🔍 데이터베이스 마이그레이션을 시작합니다...")
    
    if not os.path.exists(db_path):
        print("❌ 'spain_trip.db' 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
        return

    # DB 연결
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # 기존 데이터는 그대로 두고, phrase 테이블만 안전하게 추가 (IF NOT EXISTS)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS phrase (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category VARCHAR(50) NOT NULL,
                ko VARCHAR(200) NOT NULL,
                es VARCHAR(200) NOT NULL,
                en VARCHAR(200)
            )
        ''')
        
        conn.commit()
        print("✅ 마이그레이션 성공! 소중한 오디오 가이드 데이터는 안전하며, '회화(phrase)' 테이블만 완벽하게 추가되었습니다.")
        
    except Exception as e:
        print(f"❌ 마이그레이션 중 오류가 발생했습니다: {e}")
    finally:
        conn.close()

if __name__ == '__main__':
    upgrade_db()