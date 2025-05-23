from flask import Flask, render_template, request, jsonify
import pandas as pd
import re

app = Flask(__name__)

# ✔ 예금/적금 데이터 로드
deposit_tier1 = pd.read_csv('예금_1금융권_포함.csv')
deposit_tier2 = pd.read_csv('예금_2금융권.csv')
savings_tier1 = pd.read_csv('적금_1금융권_포함.csv')
savings_tier2 = pd.read_csv('적금_2금융권.csv')

# ✔ 지역 컬럼 매핑 추가
def normalize_name(name):
    s = str(name)
    s = re.sub(r'[㈜\s\-()]', '', s)  # 괄호, 공백, 하이픈 제거
    s = s.replace('저축은행', '').replace('은행', '').lower()
    return s

region_map_raw = {
    # 1금융권
    '국민은행':'서울','신한은행':'서울','우리은행':'서울','하나은행':'서울','농협은행':'서울',
    'SC제일은행':'서울','씨티은행':'서울','카카오뱅크':'경기','케이뱅크':'서울','토스뱅크':'서울',
    '아이엠은행':'대구','부산은행':'부산','경남은행':'경남','광주은행':'광주','전북은행':'전북','제주은행':'제주',
    # 2금융권 저축은행
    'BNK저축은행':'부산','CK저축은행':'강원','DH저축은행':'부산','HB저축은행':'서울',
    'IBK저축은행':'서울','JT저축은행':'서울','JT친애저축은행':'서울','KB저축은행':'서울',
    'MS저축은행':'서울','OK저축은행':'서울','OSB저축은행':'서울','SBI저축은행':'서울',
    '고려저축은행':'부산','국제저축은행':'부산','금화저축은행':'경기','남양저축은행':'경기',
    '다올저축은행':'서울','대명상호저축은행':'대구','대백저축은행':'대구','대신저축은행':'부산',
    '대아상호저축은행':'부산','대원저축은행':'부산','대한저축은행':'서울','더블저축은행':'서울',
    '더케이저축은행':'서울','동양저축은행':'서울','동원제일저축은행':'부산','드림저축은행':'대구',
    '디비저축은행':'서울','라온저축은행':'대전','머스트삼일저축은행':'서울','모아저축은행':'인천',
    '민국저축은행':'경기','바로저축은행':'서울','부림저축은행':'부산','삼정저축은행':'부산',
    '삼호저축은행':'서울','상상인저축은행':'서울','상상인플러스저축은행':'서울','세람저축은행':'전북',
    '센트럴저축은행':'서울','솔브레인저축은행':'대전','스마트저축은행':'광주','스카이저축은행':'서울',
    '스타저축은행':'서울','신한저축은행':'서울','아산저축은행':'충남','안국저축은행':'서울',
    '안양저축은행':'경기','애큐온저축은행':'서울','에스앤티저축은행':'경남','엔에이치저축은행':'서울',
    '영진저축은행':'대구','예가람저축은행':'서울','오성저축은행':'경기','오투저축은행':'서울',
    '우리금융저축은행':'서울','우리저축은행':'서울','웰컴저축은행':'서울','유니온저축은행':'서울',
    '유안타저축은행':'서울','융창저축은행':'서울','인성저축은행':'부산','인천저축은행':'인천',
    '조은저축은행':'광주','조흥저축은행':'서울','진주저축은행':'경남','참저축은행':'대전',
    '청주저축은행':'충북','키움예스저축은행':'서울','키움저축은행':'서울','페퍼저축은행':'서울',
    '평택저축은행':'경기','푸른저축은행':'서울','하나저축은행':'서울','한국투자저축은행':'서울',
    '한성저축은행':'서울','한화저축은행':'서울','흥국저축은행':'서울'
}
region_map = {normalize_name(k): v for k, v in region_map_raw.items()}

# 정제명 & 지역 컬럼 삽입
for df in [deposit_tier1, deposit_tier2, savings_tier1, savings_tier2]:
    df['정제명'] = df['금융회사명'].apply(normalize_name)
    df['지역'] = df['정제명'].map(region_map).fillna('기타')

# ✔ 대출 데이터 클린 및 로드
def clean_loan_data(file):
    df = pd.read_csv(file)
    df = df.rename(columns=lambda x: x.strip())
    df = df.rename(columns={
        '금리':'기본금리(%)','한도':'대출한도','상환 방식':'상환방식',
        '가입 대상':'가입대상','만기이자':'만기이자','저축기간(개월)':'저축기간(개월)'
    })
    required = ['금융회사명','상품명','기본금리(%)','대출한도','상환방식','가입대상','저축기간(개월)','만기이자']
    for c in required:
        if c not in df: df[c] = '정보 없음'
    df.dropna(subset=['금융회사명','상품명'], inplace=True)
    df.fillna('정보 없음', inplace=True)
    return df

loan_files = ['햇살론_보완완료.csv','소액비상금_대출_정리.csv','새희망홀씨_대출_정리.csv','무직자_대출_정리.csv','사잇돌_대출_정리.csv']
loan_data = pd.concat([clean_loan_data(f) for f in loan_files], ignore_index=True)

# ✔ 금융용어사전 로드 및 초성 기준
terms_df = pd.read_excel('통계용어사전.xlsx')
def get_initial_consonant(word):
    if not word: return ''
    c = word[0]
    if '가' <= c <= '힣':
        cho=['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
        return cho[(ord(c)-ord('가'))//588]
    return 'A-Z' if re.match(r'[A-Za-z]', c) else c
terms_df['초성'] = terms_df['용어'].apply(get_initial_consonant)

# 필터 유틸 함수
def filter_products(df, period, bank, region):
    if period:
        df = df[df['저축기간(개월)'] == int(period)]
    if bank:
        keys = bank.split('|')
        df = df[df['금융회사명'].isin(keys)]
    if region:
        df = df[df['지역'] == region]
    return df

# ✔ 홈
@app.route('/')
def home():
    return render_template('home_menu.html')

# ✔ 예금 라우트
@app.route('/deposits')
def deposits_page():
    periods = sorted(pd.concat([deposit_tier1, deposit_tier2])['저축기간(개월)'].unique())
    banks = {
        '1금융권': sorted(deposit_tier1['금융회사명'].unique()),
        '2금융권': sorted(deposit_tier2['금융회사명'].unique())
    }
    regions = sorted(pd.concat([deposit_tier1, deposit_tier2])['지역'].unique())
    return render_template('filter_page.html', product_type='예금', product_type_url='deposits', periods=periods, banks=banks, regions=regions)

@app.route('/deposits/detail/<product_name>')
def deposits_detail(product_name):
    df = pd.concat([deposit_tier1, deposit_tier2])
    prod = df[df['상품명'] == product_name].iloc[0]
    return render_template('product_detail.html', product=prod, product_type='예금', product_type_url='deposits')

@app.route('/api/deposits')
def api_deposits():
    period = request.args.get('period')
    bank = request.args.get('bank')
    region = request.args.get('region')
    data = pd.concat([deposit_tier1, deposit_tier2], ignore_index=True)
    filtered = filter_products(data, period, bank, region)
    products = filtered.sort_values(by='최고우대금리(%)', ascending=False).to_dict('records')
    return jsonify({'products': products, 'total': len(products)})

# ✔ 적금 라우트
@app.route('/savings')
def savings_page():
    periods = sorted(pd.concat([savings_tier1, savings_tier2])['저축기간(개월)'].unique())
    banks = {
        '1금융권': sorted(savings_tier1['금융회사명'].unique()),
        '2금융권': sorted(savings_tier2['금융회사명'].unique())
    }
    regions = sorted(pd.concat([savings_tier1, savings_tier2])['지역'].unique())
    return render_template('filter_page.html', product_type='적금', product_type_url='savings', periods=periods, banks=banks, regions=regions)

@app.route('/savings/detail/<product_name>')
def savings_detail(product_name):
    df = pd.concat([savings_tier1, savings_tier2])
    prod = df[df['상품명'] == product_name].iloc[0]
    return render_template('product_detail.html', product=prod, product_type='적금', product_type_url='savings')

@app.route('/api/savings')
def api_savings():
    period = request.args.get('period')
    bank = request.args.get('bank')
    region = request.args.get('region')
    data = pd.concat([savings_tier1, savings_tier2], ignore_index=True)
    filtered = filter_products(data, period, bank, region)
    products = filtered.sort_values(by='최고우대금리(%)', ascending=False).to_dict('records')
    return jsonify({'products': products, 'total': len(products)})

# ✔ 대출 라우트
@app.route('/loans')
def loans_page():
    return render_template('loans_list.html', products=loan_data.to_dict('records'))

@app.route('/loans/detail/<product_name>')
def loans_detail(product_name):
    prod = loan_data[loan_data['상품명'] == product_name].iloc[0]
    return render_template('product_detail.html', product=prod, product_type='대출', product_type_url='loans')

# ✔ 모아플러스 홈
@app.route('/plus')
def plus_home(): return render_template('plus_home.html')

# ✔ 모아플러스 - 금융사전
@app.route('/plus/terms')
def terms_home(): return render_template('terms_home.html', categories=sorted(terms_df['초성'].unique()))

@app.route('/plus/terms/list/<initial>')
def terms_list(initial):
    filtered = terms_df[terms_df['초성'] == initial]
    terms = filtered[['용어', '설명']].sort_values('용어').to_dict('records')
    return render_template('terms_list.html', category=initial, terms=terms)

@app.route('/plus/terms/detail/<term>')
def term_detail(term):
    row = terms_df[terms_df['용어'] == term].iloc[0]
    return render_template('term_detail.html', term=row['용어'], description=row['설명'], category='검색결과')

@app.route('/plus/terms/search')
def search_terms():
    query = request.args.get('query', '').strip()
    filtered = terms_df[terms_df['용어'].str.contains(query)]
    terms = filtered[['용어', '설명']].sort_values('용어').to_dict('records')
    return render_template('terms_list.html', category=f"검색결과: {query}", terms=terms)

@app.route('/plus/youth')
def plus_youth_policy(): return render_template('youth_policy.html')

@app.route('/plus/calculator')
def plus_calculator(): return render_template('calculator_home.html')

@app.route('/plus/section4')
def plus_section4():
    return render_template('region_map.html')
@app.route('/plus/region-data')
def region_data():
    region = request.args.get('region')
    region = region.replace("특별시", "").replace("광역시", "").replace("도", "").strip()

    # CSV 컬럼명: '시도', '가격'
    house_df = pd.read_csv('주택_시도별_보증금.csv')
    avg_prices = house_df.groupby('시도')['가격'].mean().round(1).to_dict()
    price = avg_prices.get(region, '정보없음')

    # 적금 추천
    savings = pd.concat([savings_tier1, savings_tier2])
    top_savings = savings[savings['지역'] == region].sort_values(by='최고우대금리(%)', ascending=False).head(5)
    products = top_savings[['상품명', '금융회사명', '최고우대금리(%)']].to_dict('records')

    return jsonify({'price': price, 'products': products})

@app.template_filter('extract_rate')
def extract_rate(val):
    if isinstance(val, str):
        m = re.search(r'[\d.]+', val)
        return m.group(0) if m else '0'
    return str(val)

if __name__ == '__main__':
    app.run(debug=True)
