#!/usr/bin/env python3
"""
EnvHunter - Tool untuk mengekstrak Public Environment Variables
Gunakan hanya untuk testing pada website yang Anda miliki atau memiliki izin!
"""

import requests
import re
import json
import argparse
from urllib.parse import urljoin, urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
import sys

class EnvHunter:
    def __init__(self, target_url, timeout=10, threads=20, user_agent=None):
        self.target_url = target_url.rstrip('/')
        self.timeout = timeout
        self.threads = threads
        self.user_agent = user_agent or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        self.results = {
            'html_env': [],
            'js_env': [],
            'api_keys': []
        }
        
        # Pattern untuk mendeteksi environment variables
        self.patterns = {
            'nextjs': r'NEXT_PUBLIC_([A-Z0-9_]+)\s*[:=]\s*["\']([^"\']+)["\']',
            'vite': r'VITE_([A-Z0-9_]+)\s*[:=]\s*["\']([^"\']+)["\']',
            'react': r'REACT_APP_([A-Z0-9_]+)\s*[:=]\s*["\']([^"\']+)["\']',
            'nuxt': r'NUXT_PUBLIC_([A-Z0-9_]+)\s*[:=]\s*["\']([^"\']+)["\']',
            'generic_process': r'process\.env\.([A-Z0-9_]+)',
            'generic_import': r'import\.meta\.env\.([A-Z0-9_]+)'
        }
        
        # Pattern untuk API keys (deteksi potensi key yang terekspos)
        self.api_patterns = {
            'google_api': r'AIza[0-9A-Za-z\-_]{35}',
            'aws_key': r'AKIA[0-9A-Z]{16}',
            'stripe_key': r'(?:rk|sk)_(?:live|test)_[0-9a-zA-Z]{24}',
            'github_token': r'gh[ps]_[0-9a-zA-Z]{36}',
            'slack_token': r'xox[baprs]-[0-9a-zA-Z]{10,48}',
            'jwt': r'eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+'
        }
    
    def fetch_page(self, url):
        """Fetch halaman HTML"""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"[-] Gagal fetch {url}: {str(e)}")
            return None
    
    def search_in_content(self, content, source_name):
        """Search environment variables dalam content"""
        found = []
        
        # Cari berdasarkan pattern
        for framework, pattern in self.patterns.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    if len(match) == 2:
                        var_name, var_value = match
                        found.append({
                            'source': source_name,
                            'framework': framework,
                            'variable': var_name,
                            'value': var_value
                        })
                    elif len(match) == 1:
                        found.append({
                            'source': source_name,
                            'framework': framework,
                            'variable': match[0],
                            'value': '(value not shown inline)'
                        })
                else:
                    found.append({
                        'source': source_name,
                        'framework': framework,
                        'variable': match,
                        'value': '(reference found)'
                    })
        
        # Cari API keys
        for key_type, pattern in self.api_patterns.items():
            matches = re.findall(pattern, content)
            for match in matches:
                self.results['api_keys'].append({
                    'source': source_name,
                    'type': key_type,
                    'value': match
                })
        
        return found
    
    def extract_js_files(self, html_content):
        """Ekstrak semua file JavaScript dari HTML"""
        soup = BeautifulSoup(html_content, 'html.parser')
        js_files = []
        
        # Cari script tags dengan src
        for script in soup.find_all('script', src=True):
            js_url = urljoin(self.target_url, script['src'])
            js_files.append(js_url)
        
        # Cari link preload untuk JS
        for link in soup.find_all('link', rel='preload', as_='script'):
            if link.get('href'):
                js_url = urljoin(self.target_url, link['href'])
                js_files.append(js_url)
        
        # Cari Next.js chunk files
        for script in soup.find_all('script', src=True):
            if '_next/static/chunks/' in script['src']:
                js_url = urljoin(self.target_url, script['src'])
                if js_url not in js_files:
                    js_files.append(js_url)
        
        return list(set(js_files))
    
    def scan_js_file(self, js_url):
        """Scan file JavaScript untuk environment variables"""
        print(f"[*] Scanning JS: {js_url}")
        content = self.fetch_page(js_url)
        if content:
            return self.search_in_content(content, js_url)
        return []
    
    def scan_html(self):
        """Scan HTML utama"""
        print(f"[*] Scanning HTML: {self.target_url}")
        html_content = self.fetch_page(self.target_url)
        if html_content:
            return self.search_in_content(html_content, self.target_url)
        return []
    
    def run(self):
        """Main execution"""
        print(f"""
╔═══════════════════════════════════════════╗
║         EnvHunter - Public Env Hunter     ║
║     Extract exposed environment variables ║
╚═══════════════════════════════════════════╝
""")
        print(f"[+] Target: {self.target_url}")
        print(f"[+] Timeout: {self.timeout}s")
        print(f"[+] Threads: {self.threads}")
        print("-" * 50)
        
        # 1. Scan HTML
        html_results = self.scan_html()
        self.results['html_env'].extend(html_results)
        
        # 2. Scan JavaScript files
        print(f"\n[*] Mengekstrak file JavaScript...")
        html_content = self.fetch_page(self.target_url)
        if html_content:
            js_files = self.extract_js_files(html_content)
            print(f"[+] Ditemukan {len(js_files)} file JavaScript")
            
            # Multi-threading untuk scan JS files
            with ThreadPoolExecutor(max_workers=self.threads) as executor:
                future_to_js = {executor.submit(self.scan_js_file, js_url): js_url for js_url in js_files}
                
                for future in as_completed(future_to_js):
                    js_url = future_to_js[future]
                    try:
                        js_results = future.result()
                        self.results['js_env'].extend(js_results)
                    except Exception as e:
                        print(f"[-] Error scanning {js_url}: {str(e)}")
        else:
            print("[-] Gagal mendapatkan HTML")
        
        # 3. Tampilkan hasil
        self.display_results()
    
    def display_results(self):
        """Tampilkan hasil scan"""
        print("\n" + "="*60)
        print("📊 HASIL SCAN")
        print("="*60)
        
        total_env = len(self.results['html_env']) + len(self.results['js_env'])
        
        if total_env == 0 and len(self.results['api_keys']) == 0:
            print("\n✅ Tidak ditemukan environment variables yang terekspos!")
            return
        
        # Tampilkan environment variables
        if self.results['html_env']:
            print(f"\n🔧 ENVIRONMENT VARIABLES (HTML): {len(self.results['html_env'])}")
            print("-" * 50)
            for item in self.results['html_env']:
                print(f"  [{item['framework'].upper()}] {item['variable']} = {item['value'][:50]}")
        
        if self.results['js_env']:
            print(f"\n📜 ENVIRONMENT VARIABLES (JavaScript): {len(self.results['js_env'])}")
            print("-" * 50)
            for item in self.results['js_env']:
                print(f"  [{item['framework'].upper()}] {item['variable']} = {item['value'][:50]}")
                print(f"    Source: {item['source'][:100]}")
        
        # Tampilkan API keys
        if self.results['api_keys']:
            print(f"\n⚠️  POTENSI API KEYS TEREKSPOS: {len(self.results['api_keys'])}")
            print("="*50)
            for api in self.results['api_keys']:
                print(f"  [!] {api['type'].upper()}: {api['value']}")
                print(f"      Source: {api['source'][:100]}")
    
    def save_results(self, filename):
        """Simpan hasil ke file JSON"""
        output = {
            'target': self.target_url,
            'timestamp': str(__import__('datetime').datetime.now()),
            'results': self.results
        }
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n[+] Hasil disimpan ke: {filename}")

def main():
    parser = argparse.ArgumentParser(description='EnvHunter - Extract exposed environment variables')
    parser.add_argument('url', help='Target URL (contoh: https://example.com)')
    parser.add_argument('-t', '--timeout', type=int, default=10, help='Timeout dalam detik (default: 10)')
    parser.add_argument('-o', '--output', help='Simpan hasil ke file JSON')
    parser.add_argument('--threads', type=int, default=20, help='Jumlah threads (default: 20)')
    
    args = parser.parse_args()
    
    # Validasi URL
    if not args.url.startswith(('http://', 'https://')):
        args.url = 'https://' + args.url
    
    # Jalankan scanner
    hunter = EnvHunter(args.url, timeout=args.timeout, threads=args.threads)
    hunter.run()
    
    if args.output:
        hunter.save_results(args.output)

if __name__ == "__main__":
    main()
