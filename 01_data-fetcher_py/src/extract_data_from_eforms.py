from lxml import etree
import json
import zipfile
from pathlib import Path
from typing import Dict, Optional, List, Tuple
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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

def process_zip_to_json(zip_path: Path, output_dir: Path) -> Tuple[int, int, List[str]]:
    """
    Process all XML files in a ZIP and extract to individual JSON files
    
    Args:
        zip_path: Path to the ZIP file containing eForms XML files
        output_dir: Directory where JSON files will be saved
        
    Returns:
        Tuple of (successful_count, failed_count, failed_files)
    """
    
    # Create output directory
    output_dir.mkdir(exist_ok=True, parents=True)
    
    successful_count = 0
    failed_count = 0
    failed_files = []
    
    logger.info(f"Processing ZIP file: {zip_path}")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Get all XML files in the ZIP
            xml_files = [f for f in zip_ref.namelist() if f.endswith('.xml')]
            total_files = len(xml_files)
            
            logger.info(f"Found {total_files} XML files in ZIP")
            
            for i, xml_filename in enumerate(xml_files, 1):
                try:
                    # Read XML content directly from ZIP
                    with zip_ref.open(xml_filename) as xml_file:
                        xml_content = xml_file.read()
                    
                    # Extract data using our function
                    notice_data = extract_single_notice(xml_content)
                    
                    # Generate output filename based on notice_id or XML filename
                    notice_id = notice_data.get("notice_id")
                    if notice_id:
                        json_filename = f"{notice_id}.json"
                    else:
                        # Fallback to XML filename if no notice_id
                        base_name = Path(xml_filename).stem
                        json_filename = f"{base_name}.json"
                    
                    # Save as JSON
                    json_path = output_dir / json_filename
                    with open(json_path, 'w', encoding='utf-8') as json_file:
                        json.dump(notice_data, json_file, indent=2, ensure_ascii=False)
                    
                    successful_count += 1
                    
                    # Progress logging every 100 files
                    if i % 100 == 0 or i == total_files:
                        logger.info(f"Processed {i}/{total_files} files ({successful_count} successful, {failed_count} failed)")
                
                except Exception as e:
                    failed_count += 1
                    failed_files.append(xml_filename)
                    logger.error(f"Failed to process {xml_filename}: {e}")
                    continue
    
    except zipfile.BadZipFile:
        logger.error(f"Invalid ZIP file: {zip_path}")
        return 0, 0, [str(zip_path)]
    except Exception as e:
        logger.error(f"Error processing ZIP file {zip_path}: {e}")
        return 0, 0, [str(zip_path)]
    
    logger.info(f"Processing complete: {successful_count} successful, {failed_count} failed")
    
    if failed_files:
        # Save failed files list for debugging
        failed_log_path = output_dir / "failed_files.txt"
        with open(failed_log_path, 'w') as f:
            f.write('\n'.join(failed_files))
        logger.info(f"Failed files list saved to: {failed_log_path}")
    
    return successful_count, failed_count, failed_files

def test_zip_processing():
    """Test ZIP processing with downloaded data"""
    # Use one of your downloaded ZIP files
    zip_path = Path("data/zip/eforms_2024-12.zip")  # Adjust path as needed
    output_dir = Path("data/extracted_json")
    
    if not zip_path.exists():
        logger.error(f"ZIP file not found: {zip_path}")
        return
    
    logger.info("Starting ZIP processing test...")
    successful, failed, failed_files = process_zip_to_json(zip_path, output_dir)
    
    logger.info(f"Test complete!")
    logger.info(f"Successfully processed: {successful} files")
    logger.info(f"Failed: {failed} files")
    
    if successful > 0:
        # Show a sample of the extracted files
        json_files = list(output_dir.glob("*.json"))[:3]
        logger.info(f"Sample JSON files created: {[f.name for f in json_files]}")

def test_single_file():
    """Test with the Kassel XML file"""
    xml_path = Path("data/eforms-kassel-1.xml")
    
    with open(xml_path, 'rb') as f:
        xml_content = f.read()
        
    result = extract_single_notice(xml_content)
    
    # Print with proper UTF-8 encoding
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    # # Test single file first
    # print("Testing single file extraction:")
    # test_single_file()
    
    # print("\n" + "="*50 + "\n")
    
    # Test ZIP processing
    print("Testing ZIP processing:")
    test_zip_processing()