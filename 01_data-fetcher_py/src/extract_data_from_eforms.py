from lxml import etree
import json
from pathlib import Path
from typing import Dict, Optional

def extract_single_notice(xml_content: bytes) -> Dict:
    """Extract key fields from one eForms XML notice using lxml-native approach"""
    
    # Parse the XML with lxml
    root = etree.fromstring(xml_content)
    
    # Define namespaces
    ns = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'efac': 'http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1',
        'efbc': 'http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1'
    }
    
    # Helper functions for clean extraction
    def txt(xpath: str) -> Optional[str]:
        """Extract text using XPath string() function"""
        result = root.xpath(f"string({xpath})", namespaces=ns)
        return result if result else None
    
    def attr(xpath: str, attribute: str) -> Optional[str]:
        """Extract attribute value"""
        result = root.xpath(f"{xpath}/@{attribute}", namespaces=ns)
        return result[0] if result else None
    
    def num(xpath: str) -> Optional[float]:
        """Extract number as float"""
        text = txt(xpath)
        try:
            return float(text) if text else None
        except (ValueError, TypeError):
            return None
    
    # Extract basic notice information
    notice = {
        "notice_id": txt("//cbc:ID[@schemeName='notice-id']"),
        "issue_date": txt("//cbc:IssueDate"),
        "issue_time": txt("//cbc:IssueTime"),
        "notice_type": txt("//cbc:NoticeTypeCode"),
        "regulatory_domain": txt("//cbc:RegulatoryDomain"),
        "contracting_party": {},
        "project": {},
        "lots": [],
        "financial": {}
    }
    
    # Extract contracting party
    cp_id = txt("//cac:ContractingParty//cbc:ID[@schemeName='organization']")
    if cp_id:
        cp_base = f"//efac:Organization[efac:Company/cac:PartyIdentification/cbc:ID[@schemeName='organization']='{cp_id}']/efac:Company"
        notice["contracting_party"] = {
            "name": txt(f"{cp_base}/cac:PartyName/cbc:Name[@languageID='DEU']"),
            "city": txt(f"{cp_base}/cac:PostalAddress/cbc:CityName"),
            "postal_code": txt(f"{cp_base}/cac:PostalAddress/cbc:PostalZone"),
            "nuts_code": txt(f"{cp_base}/cac:PostalAddress/cbc:CountrySubentityCode"),
            "country_code": txt(f"{cp_base}/cac:PostalAddress/cac:Country/cbc:IdentificationCode"),
            "website": txt(f"{cp_base}/cbc:WebsiteURI"),
            "buyer_type": txt("//cac:ContractingParty/cac:ContractingPartyType/cbc:PartyTypeCode"),
            "activity_type": txt("//cac:ContractingParty/cac:ContractingActivity/cbc:ActivityTypeCode")
        }
    
    # Extract project information
    proj_base = "//cac:ProcurementProject[1]"
    notice["project"] = {
        "id": txt(f"{proj_base}/cbc:ID"),
        "name": txt(f"{proj_base}/cbc:Name[@languageID='DEU']"),
        "description": txt(f"{proj_base}/cbc:Description[@languageID='DEU']"),
        "procurement_type": txt(f"{proj_base}/cbc:ProcurementTypeCode"),
        "cpv_code": txt(f"{proj_base}/cac:MainCommodityClassification/cbc:ItemClassificationCode"),
        "location": {
            "street": txt(f"{proj_base}/cac:RealizedLocation/cac:Address/cbc:StreetName"),
            "city": txt(f"{proj_base}/cac:RealizedLocation/cac:Address/cbc:CityName"),
            "postal_code": txt(f"{proj_base}/cac:RealizedLocation/cac:Address/cbc:PostalZone"),
            "nuts_code": txt(f"{proj_base}/cac:RealizedLocation/cac:Address/cbc:CountrySubentityCode"),
            "country_code": txt(f"{proj_base}/cac:RealizedLocation/cac:Address/cac:Country/cbc:IdentificationCode")
        }
    }
    
    # Extract lots
    lots = []
    for lot in root.xpath("//cac:ProcurementProjectLot", namespaces=ns):
        lot_base = "./cac:ProcurementProject"
        lot_data = {
            "id": lot.xpath("string(./cbc:ID[@schemeName='Lot'])", namespaces=ns) or None,
            "name": lot.xpath(f"string({lot_base}/cbc:Name[@languageID='DEU'])", namespaces=ns) or None,
            "description": lot.xpath(f"string({lot_base}/cbc:Description[@languageID='DEU'])", namespaces=ns) or None,
            "procurement_type": lot.xpath(f"string({lot_base}/cbc:ProcurementTypeCode)", namespaces=ns) or None,
            "cpv_code": lot.xpath(f"string({lot_base}/cac:MainCommodityClassification/cbc:ItemClassificationCode)", namespaces=ns) or None,
            "planned_period": {
                "start_date": lot.xpath(f"string({lot_base}/cac:PlannedPeriod/cbc:StartDate)", namespaces=ns) or None,
                "end_date": lot.xpath(f"string({lot_base}/cac:PlannedPeriod/cbc:EndDate)", namespaces=ns) or None
            },
            "location": {
                "street": lot.xpath(f"string({lot_base}/cac:RealizedLocation/cac:Address/cbc:StreetName)", namespaces=ns) or None,
                "city": lot.xpath(f"string({lot_base}/cac:RealizedLocation/cac:Address/cbc:CityName)", namespaces=ns) or None,
                "postal_code": lot.xpath(f"string({lot_base}/cac:RealizedLocation/cac:Address/cbc:PostalZone)", namespaces=ns) or None,
                "nuts_code": lot.xpath(f"string({lot_base}/cac:RealizedLocation/cac:Address/cbc:CountrySubentityCode)", namespaces=ns) or None,
                "country_code": lot.xpath(f"string({lot_base}/cac:RealizedLocation/cac:Address/cac:Country/cbc:IdentificationCode)", namespaces=ns) or None
            }
        }
        lots.append(lot_data)
    
    notice["lots"] = lots
    
    # Extract financial information
    fin_base = "//efac:NoticeResult"
    notice["financial"] = {
        "total_amount": num(f"{fin_base}/cbc:TotalAmount"),
        "currency": attr(f"{fin_base}/cbc:TotalAmount", "currencyID"),
        "lot_results": []
    }
    
    # Extract lot results
    for lot_result in root.xpath(f"{fin_base}/efac:LotResult", namespaces=ns):
        # Get basic lot result data
        lot_id = lot_result.xpath("string(./efac:TenderLot/cbc:ID[@schemeName='Lot'])", namespaces=ns) or None
        higher_amount = lot_result.xpath("string(./cbc:HigherTenderAmount)", namespaces=ns)
        lower_amount = lot_result.xpath("string(./cbc:LowerTenderAmount)", namespaces=ns)
        
        # Get winner
        tender_id = lot_result.xpath("string(./efac:LotTender/cbc:ID[@schemeName='tender'])", namespaces=ns)
        winner_name = None
        
        if tender_id:
            # complex relationship chain in a single XPath expression
            winner_name = root.xpath(f"""
                string(
                    //efac:Organization[
                        efac:Company/cac:PartyIdentification/cbc:ID[@schemeName='organization'] = 
                        //efac:TenderingParty[
                            cbc:ID[@schemeName='tendering-party'] = 
                            //efac:LotTender[cbc:ID[@schemeName='tender']='{tender_id}']/efac:TenderingParty/cbc:ID[@schemeName='tendering-party']
                        ]/efac:Tenderer/cbc:ID[@schemeName='organization']
                    ]/efac:Company/cac:PartyName/cbc:Name[@languageID='DEU']
                )
            """, namespaces=ns) or None
        
        notice["financial"]["lot_results"].append({
            "lot_id": lot_id,
            "contract_value": None,
            "higher_tender_amount": float(higher_amount) if higher_amount else None,
            "lower_tender_amount": float(lower_amount) if lower_amount else None,
            "winner_name": winner_name
        })
    
    return notice

def test_single_file():
    """Test with the Kassel XML file"""
    xml_path = Path("data/eforms-kassel-1.xml")
    
    with open(xml_path, 'rb') as f:
        xml_content = f.read()
        
    result = extract_single_notice(xml_content)
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_single_file()