"""
Apollo.io Enrichment Module for TTB Brands
Handles both website-based auto-enrichment and manual approval for non-website brands
"""

import os
import json
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class ApolloEnrichmentSystem:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv('APOLLO_API_KEY')
        if not self.api_key:
            logger.warning("Apollo API key not configured")

        # Target titles for Helmsman Imports outreach
        self.target_titles = [
            # C-Suite
            'owner', 'founder', 'ceo', 'chief executive',
            'president', 'managing director', 'general manager',

            # Sales & Distribution
            'vp sales', 'vice president sales', 'director of sales',
            'national sales manager', 'head of sales',
            'vp distribution', 'director of distribution',

            # Import/Export
            'import manager', 'export manager', 'import director',
            'international sales', 'global sales',

            # Business Development
            'business development', 'vp business development',
            'partnerships', 'strategic partnerships',

            # Wine/Spirits Specific
            'wine director', 'spirits director', 'beverage director',
            'portfolio manager', 'brand manager'
        ]

    def enrich_brand(self, brand_name: str, brand_data: Dict) -> Dict:
        """
        Main enrichment function that routes to appropriate track
        """
        has_website = bool(brand_data.get('enrichment_data', {}).get('url'))

        if has_website:
            return self._enrich_with_website(brand_name, brand_data)
        else:
            return self._enrich_without_website(brand_name, brand_data)

    def _enrich_with_website(self, brand_name: str, brand_data: Dict) -> Dict:
        """
        Track 1: Auto-enrichment for brands with websites
        Uses domain verification for 100% accuracy
        """
        website_url = brand_data['enrichment_data']['url']
        domain = self._extract_domain(website_url)

        try:
            # Search Apollo by domain (most accurate)
            company = self._search_company_by_domain(domain)

            if company:
                # Domain match = 100% confidence
                contacts = self._get_company_contacts(company['id'])

                return {
                    'status': 'auto_completed',
                    'confidence': 100,
                    'company': company,
                    'contacts': self._rank_contacts(contacts),
                    'verification_method': 'domain_match',
                    'requires_approval': False,
                    'enriched_date': datetime.now().isoformat()
                }
            else:
                # No company found with this domain
                return {
                    'status': 'not_found',
                    'confidence': 0,
                    'message': f'No company found in Apollo with domain: {domain}',
                    'requires_manual': True,
                    'enriched_date': datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Apollo enrichment error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'requires_manual': True
            }

    def _enrich_without_website(self, brand_name: str, brand_data: Dict) -> Dict:
        """
        Track 2: Manual approval required for brands without websites
        Provides top 5 recommendations
        """
        try:
            # Search by brand name and contextual data
            search_results = self._intelligent_company_search(brand_name, brand_data)

            if not search_results:
                return {
                    'status': 'not_found',
                    'confidence': 0,
                    'message': 'No potential matches found',
                    'requires_manual': True,
                    'manual_entry_required': True
                }

            # Calculate confidence for each match
            matches_with_confidence = []
            for company in search_results[:5]:  # Top 5 only
                confidence, match_factors = self._calculate_confidence(
                    brand_name, brand_data, company
                )

                matches_with_confidence.append({
                    'company': company,
                    'confidence': confidence,
                    'match_factors': match_factors,
                    'contacts_preview': self._get_contacts_preview(company['id'])
                })

            # Sort by confidence
            matches_with_confidence.sort(key=lambda x: x['confidence'], reverse=True)

            # Check if we have a 100% confidence match
            top_match = matches_with_confidence[0]

            if top_match['confidence'] >= 100:
                # 100% confident - auto-complete but require approval
                contacts = self._get_company_contacts(top_match['company']['id'])
                return {
                    'status': 'high_confidence_match',
                    'confidence': 100,
                    'company': top_match['company'],
                    'contacts': self._rank_contacts(contacts),
                    'match_factors': top_match['match_factors'],
                    'requires_approval': True,  # Still need human verification
                    'auto_complete_ready': True
                }
            else:
                # Less than 100% - provide recommendations
                return {
                    'status': 'recommendations',
                    'confidence': top_match['confidence'],
                    'recommendations': matches_with_confidence,
                    'requires_approval': True,
                    'requires_selection': True,
                    'message': f'Found {len(matches_with_confidence)} potential matches'
                }

        except Exception as e:
            logger.error(f"Apollo search error: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'requires_manual': True
            }

    def _search_company_by_domain(self, domain: str) -> Optional[Dict]:
        """
        Search Apollo for company by domain (most accurate method)
        """
        url = "https://api.apollo.io/v1/organizations/search"

        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

        # Search by domain using correct Apollo API parameter
        data = {
            "q_organization_domains": domain,
            "per_page": 10
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            if result.get('organizations'):
                # Filter results to find exact domain match
                for org in result['organizations']:
                    org_domain = org.get('primary_domain', '').lower().replace('www.', '')
                    search_domain = domain.lower().replace('www.', '')

                    if org_domain == search_domain:
                        return {
                            'id': org.get('id'),
                            'name': org.get('name'),
                            'domain': org.get('primary_domain'),
                            'industry': org.get('industry'),
                            'description': org.get('short_description'),
                            'employee_count': org.get('estimated_num_employees'),
                            'revenue': org.get('annual_revenue'),
                            'location': {
                                'city': org.get('city'),
                                'state': org.get('state'),
                                'country': org.get('country')
                            },
                            'website': org.get('website_url'),
                            'linkedin': org.get('linkedin_url'),
                            'founded_year': org.get('founded_year')
                        }

        return None

    def _intelligent_company_search(self, brand_name: str, brand_data: Dict) -> List[Dict]:
        """
        Multi-strategy search for companies without domain
        """
        url = "https://api.apollo.io/v1/organizations/search"

        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

        # Build search query with context
        search_queries = []

        # 1. Exact brand name
        search_queries.append(brand_name)

        # 2. Producer/Importer name if available
        if brand_data.get('importers'):
            for importer in brand_data['importers'][:1]:  # Top importer
                if importer.get('owner_name'):
                    search_queries.append(importer['owner_name'])

        # 3. Remove common suffixes and search
        clean_name = self._clean_brand_name(brand_name)
        if clean_name != brand_name:
            search_queries.append(clean_name)

        all_results = []
        seen_ids = set()

        for query in search_queries[:3]:  # Limit to 3 searches
            data = {
                "q_organization_name": query,
                "industries": ["wine", "spirits", "alcohol", "beverage", "import", "distribution"],
                "per_page": 10
            }

            # Add location filter if available
            if brand_data.get('countries'):
                country = brand_data['countries'][0]  # Primary country
                if country != 'United States':
                    data['countries'] = [country]

            try:
                response = requests.post(url, headers=headers, json=data, timeout=10)
                if response.status_code == 200:
                    result = response.json()
                    for org in result.get('organizations', []):
                        if org['id'] not in seen_ids:
                            seen_ids.add(org['id'])
                            all_results.append({
                                'id': org.get('id'),
                                'name': org.get('name'),
                                'domain': org.get('primary_domain'),
                                'industry': org.get('industry'),
                                'description': org.get('short_description'),
                                'employee_count': org.get('estimated_num_employees'),
                                'revenue': org.get('annual_revenue'),
                                'location': {
                                    'city': org.get('city'),
                                    'state': org.get('state'),
                                    'country': org.get('country')
                                },
                                'website': org.get('website_url'),
                                'search_query': query
                            })
            except:
                continue

        return all_results

    def _calculate_confidence(self, brand_name: str, brand_data: Dict, company: Dict) -> Tuple[int, Dict]:
        """
        Calculate match confidence score
        Returns: (confidence_score, match_factors)
        """
        confidence = 0
        factors = {}

        # Name similarity (40 points max)
        name_similarity = self._calculate_name_similarity(brand_name, company['name'])
        confidence += int(name_similarity * 40)
        factors['name_similarity'] = f"{int(name_similarity * 100)}%"

        # Industry match (30 points)
        if company.get('industry'):
            industry_lower = company['industry'].lower()
            if any(term in industry_lower for term in ['wine', 'spirit', 'alcohol', 'beverage', 'import', 'distribution']):
                confidence += 30
                factors['industry_match'] = True
            else:
                factors['industry_match'] = False

        # Location match (15 points)
        if brand_data.get('countries') and company.get('location', {}).get('country'):
            if company['location']['country'] in brand_data['countries']:
                confidence += 15
                factors['location_match'] = True
            else:
                factors['location_match'] = False

        # Size appropriateness (10 points)
        if company.get('employee_count'):
            if 10 <= company['employee_count'] <= 5000:  # Reasonable size for brand owner
                confidence += 10
                factors['size_appropriate'] = True

        # Has website (5 points) - indicates established business
        if company.get('website'):
            confidence += 5
            factors['has_website'] = True

        # Special case: If exact name match and alcohol industry = 100%
        if name_similarity >= 0.95 and factors.get('industry_match'):
            confidence = 100
            factors['exact_match'] = True

        return min(confidence, 100), factors

    def _get_company_contacts(self, company_id: str, limit: int = 10) -> List[Dict]:
        """
        Get contacts for a specific company
        """
        url = "https://api.apollo.io/v1/people/search"

        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

        data = {
            "organization_ids": [company_id],
            "titles": self.target_titles,
            "per_page": limit
        }

        response = requests.post(url, headers=headers, json=data, timeout=10)

        if response.status_code == 200:
            result = response.json()
            contacts = []

            for person in result.get('people', []):
                contacts.append({
                    'id': person.get('id'),
                    'name': person.get('name'),
                    'title': person.get('title'),
                    'email': person.get('email'),
                    'email_status': person.get('email_status'),
                    # Phone numbers removed to save API credits (costs 2-3x more than email)
                    # 'phone': person.get('phone_numbers', [{}])[0].get('sanitized_number') if person.get('phone_numbers') else None,
                    'linkedin': person.get('linkedin_url'),
                    'seniority': person.get('seniority'),
                    'department': person.get('departments', [''])[0] if person.get('departments') else '',
                    'location': f"{person.get('city', '')}, {person.get('state', '')}".strip(', ')
                })

            return contacts

        return []

    def _get_contacts_preview(self, company_id: str) -> List[Dict]:
        """
        Get top 2 contacts preview for recommendations
        """
        contacts = self._get_company_contacts(company_id, limit=2)
        return [
            {
                'name': c['name'],
                'title': c['title']
            } for c in contacts
        ]

    def _get_contacts_list_preview(self, company_id: str, limit: int = 50) -> List[Dict]:
        """
        Get contact list WITHOUT revealing emails (no credits used)
        Returns basic info: name, title, seniority, department
        """
        url = "https://api.apollo.io/v1/mixed_people/search"

        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

        data = {
            "organization_ids": [company_id],
            "person_titles": self.target_titles,
            "page": 1,
            "per_page": limit,
            "reveal_personal_emails": False,  # Don't reveal emails (no credits)
            "reveal_phone_number": False
        }

        response = requests.post(url, headers=headers, json=data, timeout=15)

        if response.status_code == 200:
            result = response.json()
            contacts = []

            for person in result.get('people', []):
                contacts.append({
                    'id': person.get('id'),
                    'name': person.get('name'),
                    'title': person.get('title'),
                    'seniority': person.get('seniority'),
                    'department': person.get('departments', [''])[0] if person.get('departments') else '',
                    'linkedin': person.get('linkedin_url'),
                    'location': f"{person.get('city', '')}, {person.get('state', '')}".strip(', ')
                })

            return contacts

        return []

    def _reveal_contact_emails(self, contact_ids: List[str]) -> List[Dict]:
        """
        Reveal emails for specific contacts using People Search API with reveal=true
        Credits charged: 1 per contact
        """
        url = "https://api.apollo.io/v1/people/search"

        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json',
            'X-Api-Key': self.api_key
        }

        contacts = []
        logger.info(f"Revealing emails for {len(contact_ids)} contacts using People Search API")

        for contact_id in contact_ids:
            try:
                # Use People Search API with person_ids filter and reveal flag
                data = {
                    "person_ids": [contact_id],
                    "reveal_personal_emails": True,  # This charges credits
                    "per_page": 1
                }

                logger.info(f"Calling Apollo People Search API to reveal email for contact: {contact_id}")
                response = requests.post(url, headers=headers, json=data, timeout=10)

                logger.info(f"Apollo response status: {response.status_code}")

                if response.status_code == 200:
                    result = response.json()
                    people = result.get('people', [])

                    if people:
                        person = people[0]
                        logger.info(f"Apollo returned person data for: {person.get('name')}")

                        contact_data = {
                            'id': person.get('id'),
                            'name': person.get('name'),
                            'title': person.get('title'),
                            'email': person.get('email'),
                            'email_status': person.get('email_status'),
                            'linkedin': person.get('linkedin_url'),
                            'seniority': person.get('seniority'),
                            'department': person.get('departments', [''])[0] if person.get('departments') else '',
                            'location': f"{person.get('city', '')}, {person.get('state', '')}".strip(', ')
                        }
                        contacts.append(contact_data)
                        logger.info(f"Successfully revealed contact: {contact_data.get('name')} - {contact_data.get('email')}")
                    else:
                        logger.warning(f"No person data in Apollo response for ID: {contact_id}")
                else:
                    logger.error(f"Apollo API error for contact {contact_id}: Status {response.status_code}, Response: {response.text}")
            except Exception as e:
                logger.error(f"Error revealing email for contact {contact_id}: {e}", exc_info=True)
                continue

        logger.info(f"Total contacts revealed: {len(contacts)}")
        return contacts

    def _rank_contacts(self, contacts: List[Dict]) -> List[Dict]:
        """
        Rank contacts by relevance for Helmsman Imports outreach
        """
        for contact in contacts:
            score = 0
            title_lower = (contact.get('title') or '').lower()

            # Ownership/C-Suite (highest priority)
            if any(term in title_lower for term in ['owner', 'founder', 'ceo', 'president']):
                score = 100
            # VP level
            elif 'vp' in title_lower or 'vice president' in title_lower:
                score = 90
            # Directors
            elif 'director' in title_lower:
                score = 85
            # Managers (especially import/export)
            elif 'manager' in title_lower:
                if any(term in title_lower for term in ['import', 'export', 'international']):
                    score = 80
                else:
                    score = 70
            # Sales roles
            elif 'sales' in title_lower:
                score = 75
            # Business development
            elif 'business development' in title_lower:
                score = 75
            else:
                score = 50

            contact['relevance_score'] = score
            contact['is_decision_maker'] = score >= 80

        # Sort by relevance
        contacts.sort(key=lambda x: x['relevance_score'], reverse=True)

        return contacts

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL"""
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.replace('www.', '')
        return domain.split('/')[0]

    def _clean_brand_name(self, name: str) -> str:
        """Remove common suffixes from brand name"""
        suffixes = [
            ' wines', ' wine', ' spirits', ' distillery', ' brewery',
            ' vineyards', ' vineyard', ' estates', ' estate',
            ' cellars', ' cellar', ' & co', ' co.', ' inc', ' llc'
        ]

        name_lower = name.lower()
        for suffix in suffixes:
            if name_lower.endswith(suffix):
                return name[:-(len(suffix))].strip()

        return name

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names (0-1)"""
        from difflib import SequenceMatcher

        # Normalize for comparison
        name1 = name1.lower().strip()
        name2 = name2.lower().strip()

        # Direct similarity
        direct_score = SequenceMatcher(None, name1, name2).ratio()

        # Check if one contains the other
        if name1 in name2 or name2 in name1:
            contains_score = 0.9
        else:
            contains_score = 0

        return max(direct_score, contains_score)