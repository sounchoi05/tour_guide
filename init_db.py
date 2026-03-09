import json
from app import app, db, Itinerary

def init_database():
    with app.app_context():
        # 기존 테이블을 깔끔하게 지우고 새로 생성
        db.drop_all()
        db.create_all()

        # data.json 파일 읽기
        try:
            with open('data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
        except FileNotFoundError:
            print("❌ 오류: data.json 파일을 찾을 수 없습니다.")
            return

        count = 0
        # DB에 데이터 삽입
        for item in data:
            new_itinerary = Itinerary(
                id=item.get('id'),
                city=item.get('city'),
                period=item.get('period'),
                nights=item.get('nights'),
                desc=item.get('desc'),
                tips=item.get('tips'),
                stay=item.get('stay'),
                hasParking=item.get('hasParking', False),
                routeText=item.get('routeText'),
                mapLink=item.get('mapLink'),
                mapIframe=item.get('mapIframe'),
                routeText2=item.get('routeText2'),
                mapLink2=item.get('mapLink2'),
                mapIframe2=item.get('mapIframe2'),
                parkingInfo=item.get('parkingInfo'),
                foodRecs=item.get('foodRecs'),
                under10=item.get('under10'),
                spotRecs=item.get('spotRecs'),
                shoppingRecs=item.get('shoppingRecs'),
                schedule_json=json.dumps(item.get('schedule', []), ensure_ascii=False),
                photos_json=json.dumps(item.get('photos', []), ensure_ascii=False)
            )
            db.session.add(new_itinerary)
            count += 1
        
        db.session.commit()
        print(f"✅ 성공! 총 {count}개의 도시 일정이 spain_trip.db에 저장되었습니다.")

if __name__ == '__main__':
    init_database()