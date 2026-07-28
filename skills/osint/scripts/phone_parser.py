#!/usr/bin/env python3
"""Parse and validate phone numbers without external APIs.

Detects country, carrier, line type, and generates search-optimized formats.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Optional


# Country calling codes -> country info
COUNTRY_CODES = {
    "57": {"country": "Colombia", "iso": "CO", "format": "XXX XXX XXXX", "mobile_prefixes": ["3"]},
    "52": {"country": "Mexico", "iso": "MX", "format": "XX XXXX XXXX", "mobile_prefixes": ["5"]},
    "54": {"country": "Argentina", "iso": "AR", "format": "XX XXXX XXXX", "mobile_prefixes": ["9"]},
    "56": {"country": "Chile", "iso": "CL", "format": "X XXXX XXXX", "mobile_prefixes": ["9"]},
    "51": {"country": "Peru", "iso": "PE", "format": "XXX XXX XXX", "mobile_prefixes": ["9"]},
    "593": {"country": "Ecuador", "iso": "EC", "format": "XX XXX XXXX", "mobile_prefixes": ["9"]},
    "591": {"country": "Bolivia", "iso": "BO", "format": "X XXX XXXX", "mobile_prefixes": ["6", "7"]},
    "58": {"country": "Venezuela", "iso": "VE", "format": "XXX XXX XXXX", "mobile_prefixes": ["4"]},
    "1": {"country": "USA/Canada", "iso": "US", "format": "XXX XXX XXXX", "mobile_prefixes": []},
    "34": {"country": "Spain", "iso": "ES", "format": "XXX XXX XXX", "mobile_prefixes": ["6", "7"]},
    "55": {"country": "Brazil", "iso": "BR", "format": "XX XXXXX XXXX", "mobile_prefixes": ["9"]},
    "598": {"country": "Uruguay", "iso": "UY", "format": "X XXX XXXX", "mobile_prefixes": ["9"]},
    "595": {"country": "Paraguay", "iso": "PY", "format": "XXX XXXXXX", "mobile_prefixes": ["9"]},
}

# Colombia mobile carriers by prefix (300-305 range)
COLOMBIA_CARRIERS = {
    "300": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Colombia Movil / Movistar"},
    "301": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Colombia Movil"},
    "302": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "303": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Comcel"},
    "304": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Comcel"},
    "305": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "310": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Comcel"},
    "311": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Comcel"},
    "312": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Comcel"},
    "313": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Comcel"},
    "314": {"carrier": "Claro Colombia", "type": "mobile", "old_name": "Comcel"},
    "315": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "316": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "317": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "318": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "319": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "320": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "321": {"carrier": "Movistar Colombia", "type": "mobile", "old_name": "Telefonica Moviles"},
    "322": {"carrier": "Tigo Colombia", "type": "mobile", "old_name": "Colombia Móvil / Millicom"},
    "323": {"carrier": "Tigo Colombia", "type": "mobile", "old_name": "Colombia Móvil / Millicom"},
    "324": {"carrier": "Tigo Colombia", "type": "mobile", "old_name": "Colombia Móvil / Millicom"},
    "325": {"carrier": "Tigo Colombia", "type": "mobile", "old_name": "Colombia Móvil / Millicom"},
    "350": {"carrier": "ETB", "type": "mobile", "old_name": "Empresa de Telecomunicaciones de Bogota"},
}

# Mexico carriers by prefix
MEXICO_CARRIERS = {
    "55": {"carrier": "Telcel / AT&T MX", "type": "mobile"},
    "56": {"carrier": "Telcel / AT&T MX", "type": "mobile"},
}

# USA area codes (major cities)
USA_AREA_CODES = {
    "212": "New York, NY", "213": "Los Angeles, CA", "214": "Dallas, TX",
    "215": "Philadelphia, PA", "216": "Cleveland, OH", "217": "Springfield, IL",
    "301": "Maryland", "302": "Delaware", "303": "Denver, CO", "304": "West Virginia",
    "305": "Miami, FL", "310": "Los Angeles, CA", "312": "Chicago, IL",
    "313": "Detroit, MI", "314": "St. Louis, MO", "315": "Syracuse, NY",
    "316": "Wichita, KS", "317": "Indianapolis, IN", "318": "Louisiana",
    "319": "Iowa", "323": "Los Angeles, CA", "330": "Ohio",
    "331": "Illinois", "334": "Alabama", "336": "North Carolina",
    "337": "Louisiana", "339": "Massachusetts", "347": "New York, NY",
    "351": "Massachusetts", "352": "Florida", "360": "Washington",
    "361": "Texas", "386": "Florida", "401": "Rhode Island",
    "402": "Nebraska", "404": "Atlanta, GA", "405": "Oklahoma City, OK",
    "406": "Montana", "407": "Orlando, FL", "408": "San Jose, CA",
    "409": "Texas", "410": "Baltimore, MD", "412": "Pittsburgh, PA",
    "413": "Massachusetts", "414": "Milwaukee, WI", "415": "San Francisco, CA",
    "417": "Missouri", "419": "Ohio", "423": "Tennessee",
    "424": "Los Angeles, CA", "425": "Washington", "430": "Texas",
    "432": "Texas", "434": "Virginia", "435": "Utah",
    "440": "Ohio", "442": "California", "443": "Baltimore, MD",
    "469": "Dallas, TX", "470": "Atlanta, GA", "475": "Connecticut",
    "478": "Georgia", "479": "Arkansas", "480": "Phoenix, AZ",
    "484": "Pennsylvania", "501": "Arkansas", "502": "Louisville, KY",
    "503": "Portland, OR", "504": "New Orleans, LA", "505": "New Mexico",
    "507": "Minnesota", "508": "Massachusetts", "509": "Washington",
    "510": "Oakland, CA", "512": "Austin, TX", "513": "Cincinnati, OH",
    "515": "Iowa", "516": "Long Island, NY", "517": "Michigan",
    "518": "New York", "520": "Arizona", "530": "California",
    "531": "Nebraska", "534": "Wisconsin", "539": "Oklahoma",
    "540": "Virginia", "541": "Oregon", "551": "New Jersey",
    "559": "California", "561": "Florida", "562": "California",
    "563": "Iowa", "567": "Ohio", "570": "Pennsylvania",
    "571": "Virginia", "573": "Missouri", "574": "Indiana",
    "575": "New Mexico", "580": "Oklahoma", "585": "New York",
    "586": "Michigan", "601": "Mississippi", "602": "Phoenix, AZ",
    "603": "New Hampshire", "605": "South Dakota", "606": "Kentucky",
    "607": "New York", "608": "Wisconsin", "609": "New Jersey",
    "610": "Pennsylvania", "612": "Minneapolis, MN", "614": "Columbus, OH",
    "615": "Nashville, TN", "616": "Michigan", "617": "Boston, MA",
    "618": "Illinois", "619": "San Diego, CA", "620": "Kansas",
    "623": "Arizona", "626": "California", "628": "San Francisco, CA",
    "629": "Tennessee", "630": "Illinois", "631": "Long Island, NY",
    "636": "Missouri", "641": "Iowa", "646": "New York, NY",
    "650": "California", "651": "Minnesota", "657": "California",
    "660": "Missouri", "661": "California", "662": "Mississippi",
    "667": "Maryland", "669": "California", "678": "Atlanta, GA",
    "681": "West Virginia", "682": "Texas", "701": "North Dakota",
    "702": "Las Vegas, NV", "703": "Virginia", "704": "Charlotte, NC",
    "706": "Georgia", "707": "California", "708": "Illinois",
    "712": "Iowa", "713": "Houston, TX", "714": "California",
    "715": "Wisconsin", "716": "Buffalo, NY", "717": "Pennsylvania",
    "718": "New York, NY", "719": "Colorado", "720": "Denver, CO",
    "724": "Pennsylvania", "725": "Nevada", "727": "Florida",
    "731": "Tennessee", "732": "New Jersey", "734": "Michigan",
    "737": "Texas", "740": "Ohio", "743": "North Carolina",
    "747": "California", "754": "Florida", "757": "Virginia",
    "760": "California", "762": "Georgia", "763": "Minnesota",
    "765": "Indiana", "769": "Mississippi", "770": "Georgia",
    "772": "Florida", "773": "Chicago, IL", "774": "Massachusetts",
    "775": "Nevada", "779": "Illinois", "781": "Massachusetts",
    "785": "Kansas", "786": "Miami, FL", "801": "Utah",
    "802": "Vermont", "803": "South Carolina", "804": "Virginia",
    "805": "California", "806": "Texas", "808": "Hawaii",
    "810": "Michigan", "812": "Indiana", "813": "Tampa, FL",
    "814": "Pennsylvania", "815": "Illinois", "816": "Kansas City, MO",
    "817": "Texas", "818": "California", "828": "North Carolina",
    "830": "Texas", "831": "California", "832": "Houston, TX",
    "843": "South Carolina", "845": "New York", "847": "Illinois",
    "848": "New Jersey", "850": "Florida", "854": "South Carolina",
    "856": "New Jersey", "857": "Boston, MA", "858": "California",
    "859": "Kentucky", "860": "Connecticut", "862": "New Jersey",
    "863": "Florida", "864": "South Carolina", "865": "Tennessee",
    "870": "Arkansas", "872": "Chicago, IL", "878": "Pennsylvania",
    "901": "Memphis, TN", "903": "Texas", "904": "Jacksonville, FL",
    "906": "Michigan", "907": "Alaska", "908": "New Jersey",
    "909": "California", "910": "North Carolina", "912": "Georgia",
    "913": "Kansas", "914": "New York", "915": "Texas",
    "916": "Sacramento, CA", "917": "New York, NY", "918": "Oklahoma",
    "919": "Raleigh, NC", "920": "Wisconsin", "925": "California",
    "928": "Arizona", "929": "New York, NY", "930": "Indiana",
    "931": "Tennessee", "936": "Texas", "937": "Ohio",
    "938": "Alabama", "940": "Texas", "941": "Florida",
    "947": "Michigan", "949": "California", "951": "California",
    "952": "Minnesota", "954": "Florida", "956": "Texas",
    "959": "Connecticut", "970": "Colorado", "971": "Portland, OR",
    "972": "Dallas, TX", "973": "New Jersey", "975": "Missouri",
    "978": "Massachusetts", "979": "Texas", "980": "North Carolina",
    "984": "North Carolina", "985": "Louisiana",
}


def clean_phone(phone: str) -> str:
    """Remove all non-digit characters except leading +."""
    stripped = phone.strip()
    if stripped.startswith("+"):
        return "+" + re.sub(r"[^\d]", "", stripped[1:])
    return re.sub(r"[^\d]", "", stripped)


def detect_country(phone: str) -> Optional[dict]:
    """Detect country from phone number."""
    cleaned = phone.lstrip("+")

    # Try 3-digit codes first, then 2-digit, then 1-digit
    for length in [3, 2, 1]:
        code = cleaned[:length]
        if code in COUNTRY_CODES:
            return COUNTRY_CODES[code]
    return None


def get_carrier_info(phone: str, country_iso: str) -> Optional[dict]:
    """Get carrier info for a phone number."""
    cleaned = phone.lstrip("+")

    if country_iso == "CO":
        # Remove country code (57) if present
        national = cleaned[2:] if cleaned.startswith("57") else cleaned
        prefix = national[:3]
        return COLOMBIA_CARRIERS.get(prefix)

    elif country_iso == "MX":
        national = cleaned[2:] if cleaned.startswith("52") else cleaned
        prefix = national[:2]
        return MEXICO_CARRIERS.get(prefix)

    elif country_iso == "US":
        national = cleaned[1:] if cleaned.startswith("1") else cleaned
        prefix = national[:3]
        location = USA_AREA_CODES.get(prefix)
        if location:
            return {"carrier": "US Carrier", "type": "mobile/landline", "location": location}

    return None


def format_for_search(phone: str) -> list[str]:
    """Generate multiple formats for searching."""
    cleaned = clean_phone(phone)
    digits = cleaned.lstrip("+")

    formats = []

    # E.164 format
    if cleaned.startswith("+"):
        formats.append(cleaned)

    # With country code, no +
    formats.append(digits)

    # National format variations
    if digits.startswith("57") and len(digits) == 12:
        national = digits[2:]
        formats.extend([
            f"+57 {national[:3]} {national[3:]}",
            f"+57 {national[:3]}-{national[3:]}",
            f"57 {national[:3]} {national[3:]}",
            f"57{national}",
            national,
            f"{national[:3]} {national[3:]}",
            f"{national[:3]}-{national[3:]}",
        ])
    elif digits.startswith("1") and len(digits) == 11:
        national = digits[1:]
        formats.extend([
            f"+1 {national[:3]} {national[3:6]} {national[6:]}",
            f"+1 ({national[:3]}) {national[3:6]}-{national[6:]}",
            f"({national[:3]}) {national[3:6]}-{national[6:]}",
            national,
        ])
    else:
        # Generic formatting
        if len(digits) > 6:
            mid = len(digits) // 2
            formats.extend([
                f"{digits[:mid]} {digits[mid:]}",
                f"{digits[:mid]}-{digits[mid:]}",
            ])

    return list(dict.fromkeys(formats))  # Remove duplicates, preserve order


def generate_search_queries(phone: str, country: Optional[dict] = None) -> list[str]:
    """Generate search engine queries for the phone number."""
    formats = format_for_search(phone)
    queries = []

    for fmt in formats[:4]:  # Limit to avoid noise
        queries.append(f'"{fmt}"')
        queries.append(f'"{fmt}" phone')

    if country:
        queries.append(f'"{formats[0]}" {country["country"]}')
        queries.append(f'"{formats[0]}" site:truecaller.com')
        queries.append(f'"{formats[0]}" site:whitepages.com')

    return queries[:10]


def parse_phone(phone: str) -> dict:
    """Full phone number analysis."""
    cleaned = clean_phone(phone)
    country = detect_country(cleaned)

    carrier_info = None
    if country:
        carrier_info = get_carrier_info(cleaned, country["iso"])

    formats = format_for_search(cleaned)
    queries = generate_search_queries(cleaned, country)

    # Determine line type
    line_type = "unknown"
    if carrier_info:
        line_type = carrier_info.get("type", "unknown")
    elif country and country.get("mobile_prefixes"):
        national = cleaned.lstrip("+")
        if country["iso"] == "CO":
            national = national[2:] if national.startswith("57") else national
        elif country["iso"] == "MX":
            national = national[2:] if national.startswith("52") else national
        elif country["iso"] in ("US",):
            national = national[1:] if national.startswith("1") else national

        if national[:1] in country["mobile_prefixes"]:
            line_type = "mobile (estimated)"

    return {
        "input": phone,
        "cleaned": cleaned,
        "e164": cleaned if cleaned.startswith("+") else f"+{cleaned}",
        "country": country,
        "carrier": carrier_info,
        "line_type": line_type,
        "formats": formats,
        "search_queries": queries,
        "is_valid": len(cleaned) >= 7 and country is not None,
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Phone number parser for OSINT")
    parser.add_argument("phone", nargs="?", help="Phone number to parse")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--formats", action="store_true", help="Show search formats only")
    parser.add_argument("--queries", action="store_true", help="Show search queries only")

    args = parser.parse_args()

    if not args.phone:
        phone = input("Enter phone number: ").strip()
    else:
        phone = args.phone

    result = parse_phone(phone)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif args.formats:
        for fmt in result["formats"]:
            print(fmt)
    elif args.queries:
        for q in result["search_queries"]:
            print(q)
    else:
        print(f"\n{'='*50}")
        print(f"  Phone Number Analysis: {phone}")
        print(f"{'='*50}")
        print(f"  Cleaned:       {result['cleaned']}")
        print(f"  E.164:         {result['e164']}")
        print(f"  Valid:         {'Yes' if result['is_valid'] else 'No'}")
        print(f"  Line Type:     {result['line_type']}")

        if result["country"]:
            c = result["country"]
            print(f"  Country:       {c['country']} ({c['iso']})")
            print(f"  Format:        {c['format']}")

        if result["carrier"]:
            cr = result["carrier"]
            print(f"  Carrier:       {cr['carrier']}")
            if "old_name" in cr:
                print(f"  Previous Name: {cr['old_name']}")
            if "location" in cr:
                print(f"  Location:      {cr['location']}")

        print(f"\n  Search Formats:")
        for fmt in result["formats"][:6]:
            print(f"    - {fmt}")

        print(f"\n  Search Queries:")
        for q in result["search_queries"][:6]:
            print(f"    - {q}")
        print()


if __name__ == "__main__":
    main()
