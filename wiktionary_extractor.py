#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Wiktionary German Ultra-Fast & Zero-Memory Extractor
===================================================
"""

import sys
import os
import re
import json
import bz2
import xml.etree.ElementTree as ET

def open_xml_source(file_path):
    if file_path.endswith('.bz2'):
        return bz2.open(file_path, mode='rb')
    return open(file_path, mode='rb')

def parse_wiktionary_xml(xml_file_path, output_json_path):
    if not os.path.exists(xml_file_path):
        print(f"[-] Error: File '{xml_file_path}' does not exist.")
        return

    print(f"[*] Starting streaming extraction from: {xml_file_path}")
    print(f"[*] Output will be written directly to: {output_json_path}")
    
    page_count = 0
    german_word_count = 0

    with open_xml_source(xml_file_path) as source_file, open(output_json_path, 'w', encoding='utf-8') as out_f:
        out_f.write('[\n')
        is_first_item = True

        context = ET.iterparse(source_file, events=('start', 'end'))
        _, root = next(context)  # گرفتن المان ریشه

        for event, elem in context:
            if event == 'end' and elem.tag.endswith('page'):
                page_count += 1
                
                # چاپ پیشرفت هر ۵۰۰۰ صفحه
                if page_count % 5000 == 0:
                    sys.stdout.write(f"\r[>] Pages: {page_count:,} | German Words Found: {german_word_count:,}")
                    sys.stdout.flush()

                title_elem = elem.find('.//{*}title')
                text_elem = elem.find('.//{*}text')

                title = title_elem.text if title_elem is not None else None
                text = text_elem.text if text_elem is not None else None

                if title and text and ':' not in title:
                    if '== {{Sprache|Deutsch}} ==' in text or '{{Sprache|Deutsch}}' in text:
                        
                        # Wortart
                        pos_match = re.search(r'\{\{Wortart\|([^}]+)\|Deutsch\}\}', text)
                        pos = pos_match.group(1).strip() if pos_match else "Wort"

                        # Meanings
                        meanings = []
                        for match in re.finditer(r':\[\d+\]\s*([^\n]+)', text):
                            clean_meaning = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', match.group(1))
                            clean_meaning = re.sub(r'\{\{[^}]+\}\}', '', clean_meaning).strip()
                            if clean_meaning and not clean_meaning.startswith('{{'):
                                meanings.append(clean_meaning)

                        # Examples
                        examples = []
                        example_section = re.search(r'\{\{Beispiele\}\}([\s\S]*?)(?:\{\{|\n==|$)', text)
                        if example_section:
                            for match in re.finditer(r':\[\d+\]\s*([^\n]+)', example_section.group(1)):
                                clean_ex = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', match.group(1))
                                clean_ex = re.sub(r'\'\'\'([^\']+)\'\'\'', r'\1', clean_ex)
                                clean_ex = re.sub(r'\{\{[^}]+\}\}', '', clean_ex).strip()
                                if clean_ex:
                                    examples.append(clean_ex)

                        # Idioms
                        idioms = []
                        idiom_section = re.search(r'\{\{Redewendungen\}\}([\s\S]*?)(?:\{\{|\n==|$)', text)
                        if idiom_section:
                            for match in re.finditer(r':\[\d+\]\s*([^\n]+)', idiom_section.group(1)):
                                clean_id = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', match.group(1)).strip()
                                if clean_id:
                                    idioms.append(clean_id)

                        german_word_count += 1
                        entry = {
                            "id": german_word_count,
                            "german": title,
                            "partOfSpeech": pos,
                            "definitions": meanings[:5],
                            "examples": examples[:4],
                            "idioms": idioms[:3]
                        }

                        # نوشتن مستقیم روی دیسک (بدون اشغال رم)
                        json_str = json.dumps(entry, ensure_ascii=False)
                        if not is_first_item:
                            out_f.write(',\n' + json_str)
                        else:
                            out_f.write(json_str)
                            is_first_item = False

                # پاکسازی عمیق حافظه رم
                elem.clear()
                root.clear()

        out_f.write('\n]\n')

    print(f"\n[✔] Extraction finished successfully!")
    print(f"[✔] Total pages: {page_count:,} | Total German entries: {german_word_count:,}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python wiktionary_extractor.py <input_xml_dump> <output_json_path>")
        sys.exit(1)

    parse_wiktionary_xml(sys.argv[1], sys.argv[2])
