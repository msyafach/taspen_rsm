import cv2
import pytesseract
import numpy as np
import pandas as pd
import os
import re
import matplotlib.pyplot as plt
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi Gemini API
sys_instruct = "You are a data processing assistant. Your job is to clean and structure OCR results into a tabular format that can be directly converted into a CSV file."
client = genai.Client(api_key=os.getenv('GEMINI_API'))




def preprocess_image(image_path):
    # Load image
    image = cv2.imread(image_path)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply adaptive thresholding
    thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    
    return image, gray, thresh

def detect_table_lines(thresh):
    # Detect horizontal and vertical lines
    kernel_horizontal = cv2.getStructuringElement(cv2.MORPH_RECT, (50, 1))
    kernel_vertical = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 50))

    horizontal_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_horizontal)
    vertical_lines = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_vertical)

    # Combine detected lines
    table_structure = cv2.add(horizontal_lines, vertical_lines)
    return table_structure

def enhance_with_gemini(text):
    """ Menggunakan Google Gemini untuk membersihkan hasil OCR """
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        config=types.GenerateContentConfig(system_instruction=sys_instruct),
        contents=[f"Formatkan teks hasil OCR berikut ke dalam CSV:\n{text}"]
    )
    return response.text if response else ""

def extract_text_from_image(thresh):
    # Perform OCR
    custom_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
    extracted_text = pytesseract.image_to_string(thresh, config=custom_config)
    
    print("Hasil OCR sebelum diproses:")
    print(extracted_text)
    
    # Gunakan Gemini 2.0 untuk membersihkan teks dan mengubah ke CSV
    cleaned_text = enhance_with_gemini(extracted_text)
    
    return cleaned_text

def save_to_txt(parsed_text, output_path):
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(parsed_text)
    return output_path

def main(image_path):
    # Step 1: Preprocessing
    image, gray, thresh = preprocess_image(image_path)
    
    # Step 2: Detect Table Structure
    table_lines = detect_table_lines(thresh)
    
    # Step 3: Extract Text
    extracted_text = extract_text_from_image(thresh)
    
    # Step 4: Save to TXT
    output_txt = dir_path+"output.txt"

    save_to_txt(extracted_text, output_txt)


main_path="raw_data/koran/"
for dir in os.listdir(main_path):
    if os.path.isdir(main_path+dir):
        print(dir)
        dir_img=os.listdir(main_path+dir)
        for img in sorted(dir_img, key=lambda x:int(x.split('.')[0])):
            if img.endswith(".jpg"):
                gambar_input = main_path+dir+"/"+img
                print(f"membuka direktori: {dir}")
                print(f"memproses gambar: {img}")
                dir_path=f"raw_data/koran/{dir}/"
                main(gambar_input)
            else:
                continue
