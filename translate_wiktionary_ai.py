#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
German Wiktionary AI Stream Translator (Fixed URL & Smart JSON Repair)
================================================================================
"""

import os
import sys
import json
import time
import requests
from json_repair import repair_json

API_KEY = os.getenv("GEMINI_API_KEY", "")
if not API_KEY:
    API_KEY = "YOUR_GEMINI_API_KEY_HERE"

INPUT_FILE = "wiktionary_raw.json"
OUTPUT_FILE = "wiktionary_translated.json"
PROGRESS_FILE = "translated_words.txt"

# --- تنظیمات بهینه‌شده برای Tier 1 / Paid Plan ---
BATCH_SIZE = 25
DELAY_BETWEEN_BATCHES = 0.5
ACTIVE_MODEL = "gemini-3.1-flash-lite"

def iterate_large_json_file(filepath):
    """خواندن استریم فایل‌های چند گیگابایتی با مصرف رم صفر"""
    buffer = ""
    brace_depth = 0
    in_string = False
    escape = False

    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            for char in chunk:
                if escape:
                    escape = False
                    if brace_depth > 0:
                        buffer += char
                    continue

                if char == "\\":
                    escape = True
                    if brace_depth > 0:
                        buffer += char
                    continue

                if char == '"':
                    in_string = not in_string
                    if brace_depth > 0:
                        buffer += char
                    continue

                if not in_string:
                    if char == "{":
                        if brace_depth == 0:
                            buffer = "{"
                        else:
                            buffer += char
                        brace_depth += 1
                        continue
                    elif char == "}":
                        brace_depth -= 1
                        if brace_depth == 0:
                            buffer += "}"
                            try:
                                obj = json.loads(buffer)
                                yield obj
                            except Exception:
                                pass
                            buffer = ""
                            continue

                if brace_depth > 0:
                    buffer += char

def parse_json_safely(raw_text):
    """ترمیم هوشمند JSON بدون تغییر در ساختار داده‌ها"""
    if not raw_text:
        raise ValueError("Empty response from API")

    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        try:
            repaired_str = repair_json(cleaned)
            return json.loads(repaired_str)
        except Exception as e:
            raise ValueError(f"Failed to repair JSON: {e}")

def translate_batch_with_gemini(batch_words, max_retries=5):
    # آدرس دقیق و اصل کد بدون هیچ کاراکتر اضافی
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{ACTIVE_MODEL}:generateContent?key={API_KEY}"
    simplified_input = []
    for w in batch_words:
        simplified_input.append({
            "german": w.get("german", ""),
            "pos": w.get("partOfSpeech", ""),
            "defs": w.get("definitions", [])[:2],
            "ex": w.get("examples", [])
        })

    prompt = f"""
تو یک مترجم و زبان‌شناس ارشد آلمانی به فارسی هستی.
برای هر واژه یا اصطلاح آلمانی، ترجمه و اطلاعات زیر را دقیقاً در قالب آرایه JSON خروجی بده:
- german: واژه آلمانی
- translation: معنی دقیق، طبیعی و روان به فارسی
- level: سطح تقریبی (A1, A2, B1, B2, C1, C2)
- sheetName: دسته‌بندی موضوعی به فارسی (مثلاً: اصطلاحات عامیانه، واژگان عمومی، محیط کار، پزشکی، گرامر)
- examples_fa: یک آرایه از ترجمه‌های فارسی، دقیقاً به همان تعداد و به همان ترتیبِ آرایه ورودی "ex" برای همان واژه (اگر "ex" خالی بود، examples_fa را [] بگذار).
- notes: نکته کوتاه گرامری یا آرتیکل

ورودی:
{json.dumps(simplified_input, ensure_ascii=False)}

پاسخ را صرفاً به صورت یک JSON Array از آبجکت‌ها بدون هیچ متن اضافی ارسال کن:
"""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.1,
            "max_output_tokens": 8192
        }
    }

    RETRYABLE_STATUS = {429, 500, 502, 503, 504}

    last_error = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=120)

            if resp.status_code == 200:
                text = resp.json()['candidates'][0]['content']['parts'][0]['text']
                results = parse_json_safely(text)
                break

            if resp.status_code in RETRYABLE_STATUS and attempt < max_retries:
                wait = min(90, 10 * (2 ** (attempt - 1)))
                print(f"    [~] HTTP {resp.status_code} (تلاش {attempt}/{max_retries})، "
                      f"{wait} ثانیه صبر و retry همین batch...")
                time.sleep(wait)
                last_error = Exception(f"HTTP {resp.status_code}: {resp.text}")
                continue

            raise Exception(f"HTTP {resp.status_code}: {resp.text}")

        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < max_retries:
                wait = min(90, 10 * (2 ** (attempt - 1)))
                print(f"    [~] خطای شبکه ({e.__class__.__name__}) (تلاش {attempt}/{max_retries})، "
                      f"{wait} ثانیه صبر و retry همین batch...")
                time.sleep(wait)
                continue
            raise
    else:
        raise last_error if last_error else Exception("Unknown error after retries")

    originals = {w.get("german", ""): w.get("examples", []) for w in batch_words}

    for r in results:
        german = r.get("german", "")
        original_examples = originals.get(german, [])
        examples_fa = r.get("examples_fa", [])

        if not isinstance(examples_fa, list):
            examples_fa = [examples_fa] if examples_fa else []

        if len(examples_fa) < len(original_examples):
            examples_fa = examples_fa + [""] * (len(original_examples) - len(examples_fa))
        elif len(examples_fa) > len(original_examples):
            examples_fa = examples_fa[:len(original_examples)]

        r["examples"] = original_examples
        r["examples_fa"] = examples_fa

    return results

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"[-] Error: File '{INPUT_FILE}' does not exist.")
        return

    print(f"[*] Reading from: {INPUT_FILE}")

    translated_words = set()
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as pf:
            translated_words = set(line.strip() for line in pf if line.strip())
        print(f"[+] Loaded {len(translated_words):,} already translated words.")

    out_f = open(OUTPUT_FILE, "a", encoding="utf-8")
    prog_f = open(PROGRESS_FILE, "a", encoding="utf-8")

    batch = []
    total_found = 0
    translated_count = len(translated_words)

    print(f"[*] Starting AI translation stream using {ACTIVE_MODEL}...")

    try:
        for item in iterate_large_json_file(INPUT_FILE):
            total_found += 1
            german_word = item.get("german", "").strip()

            if not german_word or german_word in translated_words:
                continue

            if len(german_word) > 100 or ":" in german_word:
                continue

            batch.append(item)

            if len(batch) >= BATCH_SIZE:
                try:
                    results = translate_batch_with_gemini(batch)
                    for r in results:
                        out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                        prog_f.write(r.get("german", "") + "\n")
                        translated_words.add(r.get("german", ""))

                    out_f.flush()
                    prog_f.flush()

                    translated_count += len(results)
                    print(f"[✓] Translated {translated_count:,} entries (scanned {total_found:,} items)...")
                    
                    time.sleep(DELAY_BETWEEN_BATCHES)

                except Exception as e:
                    print(f"[!] Error in batch (after retries): {e}")
                    failed_words = [w.get("german", "") for w in batch]
                    with open("failed_batches.log", "a", encoding="utf-8") as ff:
                        ff.write(json.dumps(failed_words, ensure_ascii=False) + "\n")
                    print(f"    [i] {len(failed_words)} واژه در failed_batches.log ثبت شد.")
                    time.sleep(5)

                batch = []

        if batch:
            try:
                results = translate_batch_with_gemini(batch)
                for r in results:
                    out_f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    prog_f.write(r.get("german", "") + "\n")
                out_f.flush()
                prog_f.flush()
            except Exception as e:
                print(f"[!] Error in final batch: {e}")

    finally:
        out_f.close()
        prog_f.close()

    print(f"\n[✔] Finished! Total translated: {translated_count:,}")

if __name__ == "__main__":
    main()