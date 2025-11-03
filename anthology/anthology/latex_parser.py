import re
import json
from typing import Dict, List, Optional, Any

class LaTeXMetadataExtractor:
    def __init__(self):
        # Patterns for different types of LaTeX macros
        self.patterns = {
            # Simple macros: \title{content}
            'simple': r'\\(\w+)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
            
            # Macros with optional parameters: \author[option]{content}
            'with_optional': r'\\(\w+)(?:\[([^\]]*)\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}',
            
            # Macros with multiple braced parameters: \affiliation{1}{content}
            'multiple_braced': r'\\(\w+)(\{[^{}]*\})+',
            
            # Complex pattern for author-like macros with trailing optional parts
            'complex_author': r'\\(\w+)(?:\[([^\]]*)\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}(?:\s*\[([^\]]*)\])?'
        }
    
    def extract_balanced_braces(self, text: str, start_pos: int) -> tuple:
        """Extract content within balanced braces starting at start_pos."""
        if start_pos >= len(text) or text[start_pos] != '{':
            return None, start_pos
        
        brace_count = 0
        content_start = start_pos + 1
        i = start_pos
        
        while i < len(text):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    return text[content_start:i], i + 1
            elif text[i] == '\\' and i + 1 < len(text):
                # Skip escaped characters
                i += 1
            i += 1
        
        return None, start_pos
    
    def extract_balanced_brackets(self, text: str, start_pos: int) -> tuple:
        """Extract content within balanced brackets starting at start_pos, handling multi-line content."""
        if start_pos >= len(text) or text[start_pos] != '[':
            return None, start_pos
        
        bracket_count = 0
        content_start = start_pos + 1
        i = start_pos
        
        while i < len(text):
            if text[i] == '[':
                bracket_count += 1
            elif text[i] == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    return text[content_start:i], i + 1
            elif text[i] == '\\' and i + 1 < len(text):
                # Skip escaped characters
                i += 1
            i += 1
        
        return None, start_pos
    
    def parse_key_value_pairs(self, content: str) -> Dict[str, str]:
        """Parse key-value pairs from optional parameter content like 'orcid=123, email=abc'."""
        if not content:
            return {}
        
        pairs = {}
        # Split by comma, but be careful about nested structures
        parts = []
        current_part = ""
        paren_count = 0
        
        for char in content:
            if char == ',' and paren_count == 0:
                parts.append(current_part.strip())
                current_part = ""
            else:
                if char in '([{':
                    paren_count += 1
                elif char in ')]}':
                    paren_count -= 1
                current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                pairs[key.strip()] = value.strip()
            elif part.strip():
                # Handle boolean flags
                pairs[part.strip()] = True
        
        return pairs
    
    def extract_author_macros(self, text: str) -> List[Dict[str, Any]]:
        """Extract author macros with their complex structure."""
        authors = []
        
        # Pattern to find author macros
        author_pattern = r'\\author(?:\[([^\]]*)\])?\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        matches = list(re.finditer(author_pattern, text, re.DOTALL))
        
        for match in matches:
            author_data = {
                'name': match.group(2).strip(),
                'affiliation_numbers': [],
                'metadata': {}
            }
            
            # Parse affiliation number from first optional parameter
            if match.group(1):
                affiliation_nums = match.group(1).strip()
                if affiliation_nums:
                    # Handle multiple affiliations like [1,2,3]
                    author_data['affiliation_numbers'] = [
                        num.strip() for num in affiliation_nums.split(',')
                    ]
            
            # Look for optional metadata block after the author name
            pos = match.end()
            while pos < len(text) and text[pos].isspace():
                pos += 1
            
            if pos < len(text) and text[pos] == '[':
                metadata_content, new_pos = self.extract_balanced_brackets(text, pos)
                if metadata_content:
                    author_data['metadata'] = self.parse_key_value_pairs(metadata_content)
            
            authors.append(author_data)
        
        return authors
    
    def extract_affiliation_macros(self, text: str) -> List[Dict[str, str]]:
        """Extract affiliation macros with number and text."""
        affiliations = []
        
        # Pattern for \affiliation{number}{text}
        affiliation_pattern = r'\\affiliation\s*\{([^}]*)\}\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        
        matches = re.finditer(affiliation_pattern, text, re.DOTALL)
        
        for match in matches:
            affiliations.append({
                'number': match.group(1).strip(),
                'text': match.group(2).strip()
            })
        
        return affiliations
    
    def extract_simple_macros(self, text: str, macro_names: List[str] = None) -> Dict[str, str]:
        """Extract simple macros like \\title{content}."""
        if macro_names is None:
            macro_names = ['title', 'keywords', 'pubyear', 'pubvolume', 'pagestart', 'pageend', 'doi', 'addbibresource']
        
        results = {}
        
        for macro_name in macro_names:
            pattern = f'\\\\{re.escape(macro_name)}\\s*\\{{([^{{}}]*(?:\\{{[^{{}}]*\\}}[^{{}}]*)*)}}'
            matches = re.findall(pattern, text, re.DOTALL)
            
            if matches:
                if len(matches) == 1:
                    results[macro_name] = matches[0].strip()
                else:
                    results[macro_name] = [match.strip() for match in matches]
        
        return results
    
    def extract_commented_macros(self, text: str) -> Dict[str, str]:
        """Extract commented out macros (starting with %)."""
        commented = {}
        
        # Pattern for commented macros like %\conferencename{...}
        pattern = r'%\\(\w+)\s*\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
        matches = re.finditer(pattern, text, re.DOTALL)
        
        for match in matches:
            macro_name = match.group(1)
            content = match.group(2).strip()
            commented[macro_name] = content
        
        return commented
    
    def extract_all_metadata(self, latex_content: str) -> Dict[str, Any]:
        """Extract all types of metadata from LaTeX content."""
        
        metadata = {
            'title': None,
            'authors': [],
            'affiliations': [],
            'keywords': None,
            'publication_info': {},
            'commented_macros': {}
        }
        
        # Extract simple macros
        simple_macros = self.extract_simple_macros(latex_content)
        
        # Organize simple macros
        if 'title' in simple_macros:
            metadata['title'] = simple_macros['title']
        if 'keywords' in simple_macros:
            metadata['keywords'] = simple_macros['keywords']
        
        # Publication information
        pub_fields = ['pubyear', 'pubvolume', 'pagestart', 'pageend', 'doi', 'addbibresource']
        for field in pub_fields:
            if field in simple_macros:
                metadata['publication_info'][field] = simple_macros[field]
        
        # Extract complex structures
        metadata['authors'] = self.extract_author_macros(latex_content)
        metadata['affiliations'] = self.extract_affiliation_macros(latex_content)
        metadata['commented_macros'] = self.extract_commented_macros(latex_content)
        
        return metadata
    
    def parse_latex_file(self, file_path: str) -> Dict[str, Any]:
        """Parse a LaTeX file and extract metadata."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            return self.extract_all_metadata(content)
        except FileNotFoundError:
            return {'error': f'File {file_path} not found'}
        except Exception as e:
            return {'error': f'Error reading file: {str(e)}'}
    
    def format_authors_with_affiliations(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Combine author information with their affiliations."""
        formatted_authors = []
        
        # Create affiliation lookup
        affiliation_lookup = {
            aff['number']: aff['text'] 
            for aff in metadata.get('affiliations', [])
        }
        
        for author in metadata.get('authors', []):
            formatted_author = {
                'name': author['name'],
                'affiliations': [],
                'metadata': author.get('metadata', {})
            }
            
            # Add affiliation text for each number
            for aff_num in author.get('affiliation_numbers', []):
                if aff_num in affiliation_lookup:
                    formatted_author['affiliations'].append({
                        'number': aff_num,
                        'text': affiliation_lookup[aff_num]
                    })
            
            formatted_authors.append(formatted_author)
        
        return formatted_authors
