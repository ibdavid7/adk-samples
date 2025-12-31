import zipfile
from bs4 import BeautifulSoup
import os
import re
import json

class EPUBNavigator:
    def __init__(self, epub_path):
        self.epub_path = epub_path
        self.z = zipfile.ZipFile(epub_path, 'r')
        self.opf_path = self._find_opf_path()
        self.spine = self._parse_spine()
        self.manifest = self._parse_manifest()
        self.page_map = self._build_page_map()

    def _find_opf_path(self):
        container_xml = self.z.read('META-INF/container.xml')
        soup = BeautifulSoup(container_xml, 'xml')
        return soup.find('rootfile')['full-path']

    def _parse_manifest(self):
        opf_content = self.z.read(self.opf_path)
        soup = BeautifulSoup(opf_content, 'xml')
        manifest = {}
        for item in soup.find_all('item'):
            manifest[item['id']] = item['href']
        return manifest

    def _parse_spine(self):
        opf_content = self.z.read(self.opf_path)
        soup = BeautifulSoup(opf_content, 'xml')
        spine = []
        for itemref in soup.find('spine').find_all('itemref'):
            spine.append(itemref['idref'])
        return spine

    def _build_page_map(self):
        """
        Scans the entire book to map page numbers (id="page_X") to (file_id, anchor_id).
        This is expensive but necessary for random access by page number.
        """
        # Check for cache
        cache_path = self.epub_path + ".pagemap.json"
        if os.path.exists(cache_path):
            print(f"Loading page map from cache: {cache_path}")
            try:
                with open(cache_path, 'r') as f:
                    # Keys in json are strings, convert back to int
                    data = json.load(f)
                    return {int(k): v for k, v in data.items()}
            except Exception as e:
                print(f"Failed to load cache: {e}. Rebuilding...")

        print(f"Building page map... (Scanning {len(self.spine)} files)")
        page_map = {}
        opf_dir = os.path.dirname(self.opf_path)

        for index, item_id in enumerate(self.spine):
            if index % 10 == 0:
                print(f"Scanning file {index + 1}/{len(self.spine)}...", end='\r')

            href = self.manifest.get(item_id)
            if not href:
                continue
            
            full_path = os.path.join(opf_dir, href) if opf_dir else href
            try:
                html_content = self.z.read(full_path).decode('utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Find all page markers
                # Assuming format <span id="page_X"/> or similar
                for span in soup.find_all('span', id=re.compile(r'^page_\d+$')):
                    page_num = int(span['id'].replace('page_', ''))
                    page_map[page_num] = {
                        'file_id': item_id,
                        'full_path': full_path,
                        'anchor_id': span['id']
                    }
            except Exception as e:
                print(f"Error scanning {full_path}: {e}")
        
        print(f"\nPage map built. Found {len(page_map)} pages.")
        
        # Save cache
        try:
            with open(cache_path, 'w') as f:
                json.dump(page_map, f)
            print(f"Saved page map cache to {cache_path}")
        except Exception as e:
            print(f"Could not save cache: {e}")

        return page_map

    def get_content_by_page_range(self, start_page, end_page):
        """
        Extracts content from start_page to end_page (inclusive).
        Returns a string of HTML/Text.
        """
        content = []
        
        # We need to iterate through the spine, starting from the file containing start_page
        # and ending at the file containing end_page.
        
        start_info = self.page_map.get(start_page)
        end_info = self.page_map.get(end_page + 1) # Look for the start of the next page
        
        if not start_info:
            return f"Error: Start page {start_page} not found."

        collecting = False
        opf_dir = os.path.dirname(self.opf_path)

        for item_id in self.spine:
            href = self.manifest.get(item_id)
            full_path = os.path.join(opf_dir, href) if opf_dir else href
            
            # Optimization: Skip files before start_page's file
            if not collecting and item_id != start_info['file_id']:
                continue
            
            try:
                html_content = self.z.read(full_path).decode('utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # If this is the start file, we need to find the start anchor
                if item_id == start_info['file_id']:
                    collecting = True
                    # Logic to start capturing from the specific anchor is complex in BS4
                    # Simplified: Capture the whole file for now, or split by ID
                    # For a robust solution, we'd traverse the tree. 
                    # Here we will just dump the text of the relevant files for the LLM to process,
                    # relying on the LLM to ignore pre-page content if we give it the marker.
                    pass

                if collecting:
                    # Extract text with some structure
                    # We want to preserve hierarchy for the context, but for the content
                    # we just want the text blocks.
                    
                    # Simple extraction:
                    text = soup.get_text(separator='\n')
                    content.append(text)
                
                # If this is the end file (or we passed it), stop
                if end_info and item_id == end_info['file_id']:
                    break
                    
            except Exception as e:
                print(f"Error reading {full_path}: {e}")

        return "\n".join(content)

    def get_hierarchy_context(self, page_number):
        """
        Scans backwards from the given page to find the active Section, Subsection, etc.
        Returns a dictionary.
        """
        context = {
            "section": None,
            "section_text": None,
            "subsection": None,
            "subsection_text": None,
            "subheading": None,
            "subheading_text": None,
            "topic": None,
            "topic_text": None
        }
        
        start_info = self.page_map.get(page_number)
        if not start_info:
            return context

        # Iterate backwards through spine
        start_index = self.spine.index(start_info['file_id'])
        opf_dir = os.path.dirname(self.opf_path)

        # We need to look at files in reverse order starting from current
        for i in range(start_index, -1, -1):
            item_id = self.spine[i]
            href = self.manifest.get(item_id)
            full_path = os.path.join(opf_dir, href) if opf_dir else href
            
            try:
                html_content = self.z.read(full_path).decode('utf-8')
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Search for headers
                # This is a heuristic. CPT structure usually maps:
                # h1 -> Section
                # h2 -> Subsection
                # h3 -> Subheading
                # h4 -> Topic
                
                # We need to find the *last* occurrence of these tags *before* our page marker
                # If we are in a previous file, it's just the last occurrence in that file.
                
                # Note: This simple search finds the last one in the file. 
                # Correct logic requires checking if it's before the page marker if in the same file.
                
                if context['topic'] is None:
                    h4 = soup.find_all('h4')
                    if h4: context['topic'] = h4[-1].get_text(strip=True)
                
                if context['subheading'] is None:
                    h3 = soup.find_all('h3')
                    if h3: context['subheading'] = h3[-1].get_text(strip=True)

                if context['subsection'] is None:
                    h2 = soup.find_all('h2')
                    if h2: context['subsection'] = h2[-1].get_text(strip=True)

                if context['section'] is None:
                    h1 = soup.find_all('h1')
                    if h1: context['section'] = h1[-1].get_text(strip=True)
                
                if all(v is not None for v in [context['section'], context['subsection'], context['subheading'], context['topic']]):
                    break
                    
            except Exception:
                continue
                
        return context

    def get_chapter_boundaries(self):
        """
        Returns a list of dicts: {'file_id': str, 'start_page': int, 'end_page': int}
        representing the page ranges for each file in the spine.
        """
        boundaries = []
        # Invert the map to group by file_id
        file_to_pages = {}
        for page_num, info in self.page_map.items():
            fid = info['file_id']
            if fid not in file_to_pages:
                file_to_pages[fid] = []
            file_to_pages[fid].append(page_num)
        
        for item_id in self.spine:
            if item_id in file_to_pages:
                pages = sorted(file_to_pages[item_id])
                boundaries.append({
                    'file_id': item_id,
                    'start_page': pages[0],
                    'end_page': pages[-1]
                })
        return boundaries
