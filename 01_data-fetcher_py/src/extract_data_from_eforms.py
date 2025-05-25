import xml.etree.ElementTree as ET
import json
from pathlib import Path
from typing import Dict, Optional, List

def safe_text(element) -> Optional[str]:
    """Safely extract text from an element"""
    return element.text if element is not None else None

def safe_attrib(element, attr: str) -> Optional[str]:
    """Safely extract attribute from an element"""
    return element.get(attr) if element is not None else None

def safe_float(text: Optional[str]) -> Optional[float]:
    """Safely convert text to float"""
    if text is None:
        return None
    try:
        return float(text)
    except (ValueError, TypeError):
        return None

def find_organization_by_id(root, org_id: str, namespaces: dict) -> Optional[ET.Element]:
    """Find organization by ID"""
    organizations = root.findall(".//efac:Organization", namespaces)
    for org in organizations:
        company = org.find("efac:Company", namespaces)
        if company is not None:
            party_id = company.find("cac:PartyIdentification/cbc:ID[@schemeName='organization']", namespaces)
            if party_id is not None and party_id.text == org_id:
                return org
    return None

def find_lot_tender_by_id(root, tender_id: str, namespaces: dict) -> Optional[ET.Element]:
    """Find LotTender by tender ID"""
    lot_tenders = root.findall(".//efac:NoticeResult/efac:LotTender", namespaces)
    for lot_tender in lot_tenders:
        tender_id_elem = lot_tender.find("cbc:ID[@schemeName='tender']", namespaces)
        if tender_id_elem is not None and tender_id_elem.text == tender_id:
            return lot_tender
    return None

def find_tendering_party_by_id(root, party_id: str, namespaces: dict) -> Optional[ET.Element]:
    """Find TenderingParty by party ID"""
    tendering_parties = root.findall(".//efac:NoticeResult/efac:TenderingParty", namespaces)
    for party in tendering_parties:
        party_id_elem = party.find("cbc:ID[@schemeName='tendering-party']", namespaces)
        if party_id_elem is not None and party_id_elem.text == party_id:
            return party
    return None

def extract_single_notice(xml_content: bytes) -> Dict:
    """Extract key fields from one eForms XML notice"""
    
    # Parse the XML
    root = ET.fromstring(xml_content)
    
    # Define namespaces from the XML
    namespaces = {
        'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
        'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
        'efac': 'http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1',
        'efbc': 'http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1'
    }
    
    # Start with an empty notice structure
    notice = {
        "notice_id": None,
        "issue_date": None,
        "issue_time": None,
        "notice_type": None,
        "regulatory_domain": None,
        "contracting_party": {},
        "project": {},
        "lots": [],
        "financial": {}
    }
    
    # Extract basic notice information
    notice["notice_id"] = safe_text(root.find("cbc:ID[@schemeName='notice-id']", namespaces))
    notice["issue_date"] = safe_text(root.find("cbc:IssueDate", namespaces))
    notice["issue_time"] = safe_text(root.find("cbc:IssueTime", namespaces))
    notice["notice_type"] = safe_text(root.find("cbc:NoticeTypeCode", namespaces))
    notice["regulatory_domain"] = safe_text(root.find("cbc:RegulatoryDomain", namespaces))
    
    # Extract contracting party information
    contracting_party_id = safe_text(root.find("cac:ContractingParty/cac:Party/cac:PartyIdentification/cbc:ID[@schemeName='organization']", namespaces))
    
    if contracting_party_id:
        # Find the organization details
        org_elem = find_organization_by_id(root, contracting_party_id, namespaces)
        
        if org_elem is not None:
            company = org_elem.find("efac:Company", namespaces)
            if company is not None:
                notice["contracting_party"] = {
                    "name": safe_text(company.find("cac:PartyName/cbc:Name[@languageID='DEU']", namespaces)),
                    "city": safe_text(company.find("cac:PostalAddress/cbc:CityName", namespaces)),
                    "postal_code": safe_text(company.find("cac:PostalAddress/cbc:PostalZone", namespaces)),
                    "nuts_code": safe_text(company.find("cac:PostalAddress/cbc:CountrySubentityCode", namespaces)),
                    "country_code": safe_text(company.find("cac:PostalAddress/cac:Country/cbc:IdentificationCode", namespaces)),
                    "website": safe_text(company.find("cbc:WebsiteURI", namespaces)),
                    "buyer_type": safe_text(root.find("cac:ContractingParty/cac:ContractingPartyType/cbc:PartyTypeCode", namespaces)),
                    "activity_type": safe_text(root.find("cac:ContractingParty/cac:ContractingActivity/cbc:ActivityTypeCode", namespaces))
                }
    
    # Extract project information (top-level procurement project)
    project_elem = root.find("cac:ProcurementProject", namespaces)
    if project_elem is not None:
        notice["project"] = {
            "id": safe_text(project_elem.find("cbc:ID", namespaces)),
            "name": safe_text(project_elem.find("cbc:Name[@languageID='DEU']", namespaces)),
            "description": safe_text(project_elem.find("cbc:Description[@languageID='DEU']", namespaces)),
            "procurement_type": safe_text(project_elem.find("cbc:ProcurementTypeCode", namespaces)),
            "cpv_code": safe_text(project_elem.find("cac:MainCommodityClassification/cbc:ItemClassificationCode", namespaces)),
            "location": {
                "street": safe_text(project_elem.find("cac:RealizedLocation/cac:Address/cbc:StreetName", namespaces)),
                "city": safe_text(project_elem.find("cac:RealizedLocation/cac:Address/cbc:CityName", namespaces)),
                "postal_code": safe_text(project_elem.find("cac:RealizedLocation/cac:Address/cbc:PostalZone", namespaces)),
                "nuts_code": safe_text(project_elem.find("cac:RealizedLocation/cac:Address/cbc:CountrySubentityCode", namespaces)),
                "country_code": safe_text(project_elem.find("cac:RealizedLocation/cac:Address/cac:Country/cbc:IdentificationCode", namespaces))
            }
        }
    
    # Extract lots information
    lots = []
    lot_elements = root.findall("cac:ProcurementProjectLot", namespaces)
    
    for lot_elem in lot_elements:
        lot_project = lot_elem.find("cac:ProcurementProject", namespaces)
        if lot_project is not None:
            planned_period = lot_project.find("cac:PlannedPeriod", namespaces)
            
            lot_data = {
                "id": safe_text(lot_elem.find("cbc:ID[@schemeName='Lot']", namespaces)),
                "name": safe_text(lot_project.find("cbc:Name[@languageID='DEU']", namespaces)),
                "description": safe_text(lot_project.find("cbc:Description[@languageID='DEU']", namespaces)),
                "procurement_type": safe_text(lot_project.find("cbc:ProcurementTypeCode", namespaces)),
                "cpv_code": safe_text(lot_project.find("cac:MainCommodityClassification/cbc:ItemClassificationCode", namespaces)),
                "planned_period": {
                    "start_date": safe_text(planned_period.find("cbc:StartDate", namespaces)) if planned_period is not None else None,
                    "end_date": safe_text(planned_period.find("cbc:EndDate", namespaces)) if planned_period is not None else None
                },
                "location": {
                    "street": safe_text(lot_project.find("cac:RealizedLocation/cac:Address/cbc:StreetName", namespaces)),
                    "city": safe_text(lot_project.find("cac:RealizedLocation/cac:Address/cbc:CityName", namespaces)),
                    "postal_code": safe_text(lot_project.find("cac:RealizedLocation/cac:Address/cbc:PostalZone", namespaces)),
                    "nuts_code": safe_text(lot_project.find("cac:RealizedLocation/cac:Address/cbc:CountrySubentityCode", namespaces)),
                    "country_code": safe_text(lot_project.find("cac:RealizedLocation/cac:Address/cac:Country/cbc:IdentificationCode", namespaces))
                }
            }
            lots.append(lot_data)
    
    notice["lots"] = lots
    
    # Extract financial information - FIXED XPATH
    total_amount_elem = root.find(".//efac:NoticeResult/cbc:TotalAmount", namespaces)
    
    financial_data = {
        "total_amount": safe_float(safe_text(total_amount_elem)),
        "currency": safe_attrib(total_amount_elem, "currencyID"),
        "lot_results": []
    }
    
    # Extract lot results with winner information - FIXED WITH MANUAL SEARCH
    lot_results = root.findall(".//efac:NoticeResult/efac:LotResult", namespaces)
    for lot_result in lot_results:
        lot_id_elem = lot_result.find("efac:TenderLot/cbc:ID[@schemeName='Lot']", namespaces)
        higher_amount_elem = lot_result.find("cbc:HigherTenderAmount", namespaces)
        lower_amount_elem = lot_result.find("cbc:LowerTenderAmount", namespaces)
        
        # Simplified winner extraction using manual search
        winner_name = None
        tender_id_elem = lot_result.find("efac:LotTender/cbc:ID[@schemeName='tender']", namespaces)
        
        if tender_id_elem is not None:
            tender_id = tender_id_elem.text
            
            # Find the corresponding LotTender
            lot_tender = find_lot_tender_by_id(root, tender_id, namespaces)
            if lot_tender is not None:
                tendering_party_id_elem = lot_tender.find("efac:TenderingParty/cbc:ID[@schemeName='tendering-party']", namespaces)
                if tendering_party_id_elem is not None:
                    tendering_party_id = tendering_party_id_elem.text
                    
                    # Find the tendering party
                    tendering_party = find_tendering_party_by_id(root, tendering_party_id, namespaces)
                    if tendering_party is not None:
                        tenderer_org_id_elem = tendering_party.find("efac:Tenderer/cbc:ID[@schemeName='organization']", namespaces)
                        if tenderer_org_id_elem is not None:
                            winner_org = find_organization_by_id(root, tenderer_org_id_elem.text, namespaces)
                            if winner_org is not None:
                                company = winner_org.find("efac:Company", namespaces)
                                if company is not None:
                                    winner_name = safe_text(company.find("cac:PartyName/cbc:Name[@languageID='DEU']", namespaces))
        
        lot_result_data = {
            "lot_id": safe_text(lot_id_elem),
            "contract_value": None,  # Could extract from settled contracts if needed
            "higher_tender_amount": safe_float(safe_text(higher_amount_elem)),
            "lower_tender_amount": safe_float(safe_text(lower_amount_elem)),
            "winner_name": winner_name
        }
        financial_data["lot_results"].append(lot_result_data)
    
    notice["financial"] = financial_data
    
    return notice

def test_single_file():
    """Test with the Kassel XML file"""
    xml_path = Path("data/eforms-kassel-1.xml")
    
    with open(xml_path, 'rb') as f:
        xml_content = f.read()
        
    result = extract_single_notice(xml_content)
    
    # Print with proper UTF-8 encoding
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_single_file()