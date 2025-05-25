import xml.etree.ElementTree as ET
import json
from pathlib import Path
from typing import Dict, Optional

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
    
    # Extract basic fields using proper Python syntax
    notice_id_elem = root.find(".//cbc:ID[@schemeName='notice-id']", namespaces)
    notice["notice_id"] = notice_id_elem.text if notice_id_elem is not None else None
    
    issue_date_elem = root.find(".//cbc:IssueDate", namespaces)
    notice["issue_date"] = issue_date_elem.text if issue_date_elem is not None else None
    
    issue_time_elem = root.find(".//cbc:IssueTime", namespaces)
    notice["issue_time"] = issue_time_elem.text if issue_time_elem is not None else None
    
    return notice

def test_single_file():
    """Test with the Kassel XML file"""
    xml_path = Path("data/eforms-kassel-1.xml")
    
    with open(xml_path, 'rb') as f:
        xml_content = f.read()
        
    result = extract_single_notice(xml_content)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    test_single_file()