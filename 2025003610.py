import pandas as pd
import requests
import matplotlib.pyplot as plt
import folium
from datetime import datetime
import os

# [환경 설정] 시각화 한글 깨짐 방지
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

class PopulationAnalyzer:
    """
    프로젝트명: 공공데이터 기반 실시간 지역 인구 및 소멸 위험 분석기
    작성자: 국미승 (학번: 2025003610)
    """

    def __init__(self):
        # 행정안전부 공공데이터 Open API 정보
        self.url = "https://api.odcloud.kr/api/15061057/v1/uddi:d3106ebc-3d23-424d-84f5-5a522501a4e1_201909181116"
        self.api_key = "YOUR_API_KEY" # 개인 보안을 위해 환경변수 또는 샘플 모드 권장
        self.df = None
        
        # 실제 지도 표시를 위한 지역별 위경도 좌표 데이터 매핑
        self.location_coords = {
            '서울특별시': [37.5665, 126.9780], '부산광역시': [35.1796, 129.0756],
            '대구광역시': [35.8714, 128.6014], '인천광역시': [37.4563, 126.7052],
            '광주광역시': [35.1595, 126.8526], '대전광역시': [36.3504, 127.3845],
            '울산광역시': [35.5384, 129.3114], '세종특별자치시': [36.4800, 127.2890],
            '경기도': [37.4138, 127.5183], '강원특별자치도': [37.8228, 128.1555],
            '충청북도': [36.6353, 127.4913], '충청남도': [36.6588, 126.6728],
            '전북특별자치도': [35.8204, 127.1087], '전라남도': [34.8160, 126.4629],
            '경상북도': [36.5760, 128.5056], '경상남도': [35.2377, 128.6924],
            '제주특별자치도': [33.4890, 126.4983]
        }

    def fetch_data(self):
        """FR-01: 외부 데이터 수집 및 NFR-01 예외 처리"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 데이터 수집 엔진 가동 중...")
        try:
            params = {'page': 1, 'perPage': 20, 'serviceKey': self.api_key}
            response = requests.get(self.url, params=params, timeout=10)
            
            if response.status_code == 200:
                self.df = pd.DataFrame(response.json()['data'])
                return True
            else:
                raise Exception("API 서버 통신 실패")
        except:
            # NFR-01: 네트워크 단절 시 대체 샘플 데이터 로드
            print("! [NFR-01 확인] 실시간 API 연결 불가. 로컬 시뮬레이션 데이터를 로드합니다.")
            sample = {
                '행정구역': list(self.location_coords.keys()),
                '총 인구수': ['9,411,260', '3,290,120', '2,350,440', '2,980,110', '1,410,550', '1,440,220', '1,100,330', '380,440', '13,600,000', '1,530,220', '1,590,110', '2,120,440', '1,750,330', '1,790,550', '2,540,110', '3,250,880', '670,220'],
                '65세 이상 인구수': ['1,750,000', '760,000', '520,000', '510,000', '250,000', '280,000', '180,000', '40,000', '2,100,000', '360,000', '330,000', '460,000', '410,000', '470,000', '620,000', '680,000', '120,000'],
                '가임 여성인구': ['1,100,000', '310,000', '220,000', '320,000', '140,000', '150,000', '110,000', '55,000', '1,800,000', '80,000', '120,000', '160,000', '110,000', '85,000', '130,000', '210,000', '65,000']
            }
            self.df = pd.DataFrame(sample)
            return True

    def process_data(self):
        """FR-02: 데이터 전처리 및 지표 산출"""
        for col in ['총 인구수', '65세 이상 인구수', '가임 여성인구']:
            self.df[col] = self.df[col].astype(str).str.replace(',', '').astype(int)
        
        self.df['고령화 비율(%)'] = (self.df['65세 이상 인구수'] / self.df['총 인구수']) * 100
        self.df['소멸위험지수'] = self.df['가임 여성인구'] / self.df['65세 이상 인구수']
        self.df = self.df.sort_values(by='고령화 비율(%)', ascending=False)

    def generate_outputs(self):
        """FR-03: 결과 시각화 및 멀티 리포트 저장"""
        # 엑셀 저장을 시각화보다 먼저 수행하여 데이터 유실 방지
        f_name = f"result_{datetime.now().strftime('%Y%m%d')}.xlsx"
        self.df.to_excel(f_name, index=False)
        
        # 지도 리포트 생성
        m = folium.Map(location=[36.5, 127.5], zoom_start=7, tiles='cartodbpositron')
        for _, row in self.df.iterrows():
            name = row['행정구역']
            if name in self.location_coords:
                idx = row['소멸위험지수']
                color = 'red' if idx < 0.5 else ('orange' if idx < 1.0 else 'blue')
                folium.CircleMarker(
                    location=self.location_coords[name],
                    radius=row['고령화 비율(%)'] * 0.8,
                    popup=f"<b>{name}</b><br>고령화: {row['고령화 비율(%)']:.1f}%<br>소멸지수: {idx:.2f}",
                    color=color, fill=True, fill_opacity=0.6
                ).add_to(m)
        m.save("population_analysis_map.html")
        print(f"분석 완료: 엑셀({f_name}) 및 지도(html)가 성공적으로 저장되었습니다.")

        # Matplotlib 이중 축 시각화
        fig, ax1 = plt.subplots(figsize=(14, 7))
        ax1.bar(self.df['행정구역'], self.df['총 인구수'], color='lightsteelblue', label='총 인구수')
        ax1.set_ylabel('인구 수 (명)')
        plt.xticks(rotation=45)
        ax2 = ax1.twinx()
        ax2.plot(self.df['행정구역'], self.df['고령화 비율(%)'], color='crimson', marker='o', label='고령화 비율')
        ax2.set_ylabel('고령화 비율 (%)')
        plt.title(f"지역별 인구 현황 분석 리포트 ({datetime.now().strftime('%Y-%m')})")
        fig.tight_layout()
        print("그래프 창을 닫으면 프로그램이 안전하게 종료됩니다.")
        plt.show()

if __name__ == "__main__":
    app = PopulationAnalyzer()
    if app.fetch_data():
        app.process_data()
        app.generate_outputs()