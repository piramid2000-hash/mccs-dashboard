import requests

class SeionMatMCP:
    def __init__(self):
        # 미국 국립보건원(NIH) 산하 PubChem 데이터베이스 무료 공식 API 직결선
        self.base_url = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
        print("🧪 [Seion MatMCP] 글로벌 화학/소재 데이터베이스 통신망 연결 완료!")

    def fetch_material_data(self, material_name):
        """특정 물질의 이름을 입력하면, 전 세계 데이터를 뒤져서 화학적 특성을 뽑아옵니다."""
        print(f"🔍 글로벌 DB에서 [{material_name}] 물리화학적 특성 검색 중...")
        
        try:
            # 1단계: 물질 이름으로 고유 식별자(CID) 찾기
            search_url = f"{self.base_url}/compound/name/{material_name}/cids/JSON"
            res = requests.get(search_url)
            
            if res.status_code != 200:
                return f"❌ '{material_name}'에 대한 데이터를 글로벌 DB에서 찾을 수 없습니다."
                
            cid = res.json()['IdentifierList']['CID'][0]

            # 2단계: 식별자로 정확한 분자식, 중량, 구조식(SMILES) 긁어오기
            prop_url = f"{self.base_url}/compound/cid/{cid}/property/MolecularFormula,MolecularWeight,IsomericSMILES/JSON"
            prop_res = requests.get(prop_url)
            props = prop_res.json()['PropertyTable']['Properties'][0]

            result = (
                f"✅ [MatMCP 검색 결과 도출]\n"
                f" - 물질명: {material_name}\n"
                f" - 분자식: {props.get('MolecularFormula')}\n"
                f" - 분자량: {props.get('MolecularWeight')} g/mol\n"
                f" - 분자구조(SMILES): {props.get('IsomericSMILES')}"
            )
            return result
            
        except Exception as e:
            return f"❌ API 통신 오류 발생: {e}"

# ---------------------------------------------------------
# 단독 실행 테스트 (맥미니가 화학 박사가 되는 순간!)
# ---------------------------------------------------------
if __name__ == "__main__":
    mcp = SeionMatMCP()
    
    # 소장님의 MCCS 핵심 소재인 '탄산칼륨(K2CO3)'을 영어 학명으로 검색해 봅니다!
    target_material = "Potassium carbonate" 
    
    print("-" * 50)
    # 진짜로 글로벌 DB에서 데이터를 뽑아옵니다!
    material_report = mcp.fetch_material_data(target_material)
    print(material_report)
    print("-" * 50)
