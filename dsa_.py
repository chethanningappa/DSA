import json
import csv
import os
import datetime
import re
from GetRawAnswer import GetRawAnswer
from pathlib import Path

def get_raw_answers_pipeline(
    json_file_path: str,
    project_code: str,
    file_code: str,
    question_db_path: str,
    model_key: str,
    output_base_dir: str = r"C:\Users\cheth\Documents\save",
    access_type: str = 'info'
):
    """
    Main pipeline for extracting raw answers from JSON transcription files.
    
    Args:
        json_file_path: Path to JSON transcription file
        project_code: Project identifier code (e.g., "DYQVSQ")
        file_code: File identifier code (e.g., "TXT_110303")
        question_db_path: Path to question database CSV file
        model_key: OpenAI API key for model access
        output_base_dir: Base directory for saving outputs
        access_type: Access type for GetRawAnswer ('info', 'debug', etc.)
    
    Returns:
        Tuple of (results_data, output_files_dict, status_dict)
    """
    
    # Initialize status tracking
    status = {
        "success": False,
        "message": "",
        "error": None,
        "files_created": []
    }
    
    try:
        print("="*60)
        print(f" STARTING PROCESSING PIPELINE")
        print("="*60)
        print(f"Project Code: {project_code}")
        print(f"File Code: {file_code}")
        print(f"Input File: {Path(json_file_path).name}")
        
        # ----------------------------
        # 1. Initialize GetRawAnswer
        # ----------------------------
        print(f"\n Initializing GetRawAnswer...")
        tti = GetRawAnswer(access_type=access_type)
        
        # ----------------------------
        # 2. Load and Parse JSON Data
        # ----------------------------
        print(f"\n Loading JSON data...")
        with open(json_file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Extract texts
        english_text = json_data.get("transcribed_text", "")
        original_lang_text = json_data.get("original_lang_transcribed_text", "")
        
        print(f" English text length: {len(english_text)} chars")
        print(f" Original language text length: {len(original_lang_text)} chars")
        
        if not english_text:
            raise ValueError("No English text found in JSON file")
        
        # ----------------------------
        # 3. Extract Metadata from Filename
        # ----------------------------
        print(f"\n Extracting metadata...")
        filename = Path(json_file_path).stem
        
        # Parse filename for date and time
        pattern = r'Owner_XUV700_[A-Z0-9]+_[A-Z]{2}_(\d{2}-\d{2}-\d{4}) (\d{2}_\d{2}_\d{2})'
        match = re.search(pattern, filename)
        
        if match:
            date_str = match.group(1)  # e.g., 31-10-2025
            time_str = match.group(2)  # e.g., 14_10_20
        else:
            date_str = datetime.datetime.now().strftime("%d-%m-%Y")
            time_str = datetime.datetime.now().strftime("%H_%M_%S")
        
        print(f" Date: {date_str}")
        print(f" Time: {time_str}")
        
        # ----------------------------
        # 4. Prepare Parameters
        # ----------------------------
        print(f"\n Preparing parameters...")
        
        data_parameters = {
            "data": english_text,
            "data_type": "str",
            "mode": "paragraph",
            "org_lang_data": original_lang_text,
            "file_name": f"{project_code}_{file_code}"
        }
        
        pre_processing_parameters = {
            "non_en_lang": 1
        }
        
        company_brand_info_parameters = {
            "focal_company_brand_info": {
                "Mahindra": ["XUV 700"]
            },
            "competitor_company_brand_info": {
                "Mahindra": ["Bolero", "Thar", "XUV 300"],
                "Tata": ["Nexon"]
            },
            "aliases": {
                "XUV": ["xcv", "xcb", "xev", "xt-v", "xevw"],
                "XUV 300": ["xuv300", "xuv-300", "xuv:300", "3oo"],
                "XUV 700": ["xuv700", "xuv-700", "xuv:700", "7oo"]
            }
        }
        
        question_db_parameters = {
            "question_db": question_db_path,
            "question_db_type": "csv",
            "get_verbatim_answers": 1,
            "high_complexity": 1
        }
        
        model_parameters = {
            "model_key": model_key
        }
        
        # ----------------------------
        # 5. Get Raw Answers
        # ----------------------------
        print(f"\n Extracting raw answers...")
        result, status_code, message = tti.get_raw_answers(
            data_parameters=data_parameters,
            pre_processing_parameters=pre_processing_parameters,
            company_brand_info_parameters=company_brand_info_parameters,
            question_db_parameters=question_db_parameters,
            model_parameters=model_parameters
        )
        
        print(f"Processing complete!")
        print(f"Status Code: {status_code}")
        print(f"Message: {message}")
        print(f"Questions Answered: {len(result)}")
        
        # ----------------------------
        # 6. Create Output Directory Structure
        # ----------------------------
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        date_formatted = date_str.replace('-', '')
        time_formatted = time_str.replace('_', '')
        
        # Create project-specific directory
        project_output_dir = os.path.join(output_base_dir, project_code)
        os.makedirs(project_output_dir, exist_ok=True)
        
        # Create date-specific subdirectory
        date_output_dir = os.path.join(project_output_dir, date_formatted)
        os.makedirs(date_output_dir, exist_ok=True)
        
        output_files = {}
        
        # ----------------------------
        # 7. Save CSV Results
        # ----------------------------
        csv_filename = f"{project_code}_{file_code}_{date_formatted}_{time_formatted}.csv"
        csv_filepath = os.path.join(date_output_dir, csv_filename)
        
        print(f"\n Saving CSV results...")
        if result and isinstance(result, list):
            save_questions_to_csv(
                data=result,
                output_path=csv_filepath
            )
            output_files['csv'] = csv_filepath
            status["files_created"].append(csv_filepath)
        
        # ----------------------------
        # 8. Save JSON Results
        # ----------------------------
        json_filename = f"{project_code}_{file_code}_{date_formatted}_{time_formatted}.json"
        json_filepath = os.path.join(date_output_dir, json_filename)
        
        print(f"\n Saving JSON results...")
        with open(json_filepath, "w", encoding="utf-8") as f:
            metadata = {
                "metadata": {
                    "project_code": project_code,
                    "file_code": file_code,
                    "original_filename": Path(json_file_path).name,
                    "date": date_str,
                    "time": time_str,
                    "processing_timestamp": timestamp,
                    "english_text_length": len(english_text),
                    "hindi_text_length": len(original_lang_text),
                    "questions_answered": len(result) if result else 0,
                    "status_code": status_code,
                    "message": message
                },
                "results": result if result else []
            }
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        output_files['json'] = json_filepath
        status["files_created"].append(json_filepath)
        
        # ----------------------------
        # 9. Save Summary Report
        # ----------------------------
        summary_filename = f"SUMMARY_{project_code}_{file_code}_{timestamp}.txt"
        summary_filepath = os.path.join(date_output_dir, summary_filename)
        
        print(f"\n Generating summary report...")
        with open(summary_filepath, "w", encoding="utf-8") as f:
            f.write(f"PROCESSING SUMMARY REPORT\n")
            f.write("="*60 + "\n")
            f.write(f"Project Code: {project_code}\n")
            f.write(f"File Code: {file_code}\n")
            f.write(f"Date: {date_str}\n")
            f.write(f"Time: {time_str}\n")
            f.write(f"Original File: {Path(json_file_path).name}\n")
            f.write(f"Processing Timestamp: {timestamp}\n")
            f.write("\n" + "="*60 + "\n")
            f.write("TEXT STATISTICS:\n")
            f.write(f"  English Text Length: {len(english_text)} characters\n")
            f.write(f"  Hindi Text Length: {len(original_lang_text)} characters\n")
            f.write("\n" + "="*60 + "\n")
            f.write("PROCESSING RESULTS:\n")
            f.write(f"  Status Code: {status_code}\n")
            f.write(f"  Message: {message}\n")
            f.write(f"  Questions Answered: {len(result) if result else 0}\n")
            f.write("\n" + "="*60 + "\n")
            f.write("OUTPUT FILES:\n")
            f.write(f"  1. CSV Results: {csv_filepath}\n")
            f.write(f"  2. JSON Results: {json_filepath}\n")
            f.write(f"  3. Summary Report: {summary_filepath}\n")
            f.write("\n" + "="*60 + "\n")
            f.write("SAMPLE ANSWERS:\n")
            if result and len(result) > 0:
                for i, item in enumerate(result[:3]):
                    f.write(f"\nQ{i+1}: {item.get('Questionnaire', 'N/A')}\n")
                    f.write(f"  Answer: {item.get('Raw_Answers', 'N/A')}\n")
                    f.write("-"*50 + "\n")
        
        output_files['summary'] = summary_filepath
        status["files_created"].append(summary_filepath)
        
        # ----------------------------
        # 10. Display Results Summary
        # ----------------------------
        print(f"\n PROCESSING COMPLETE!")
        print("="*60)
        print(f" Output Directory: {date_output_dir}")
        print(f" Files Created:")
        for i, filepath in enumerate(status["files_created"], 1):
            print(f"  {i}. {os.path.basename(filepath)}")
        
        if result and len(result) > 0:
            print(f"\n Sample Results (First 2 questions):")
            for i, item in enumerate(result[:2]):
                print(f"\nQ{i+1}: {item.get('Questionnaire', 'N/A')}")
                print(f"  Answer: {item.get('Raw_Answers', 'N/A')[:80]}...")
        
        status["success"] = True
        status["message"] = f"Successfully processed {len(result) if result else 0} questions"
        
        return result, output_files, status
        
    except Exception as e:
        error_msg = f"Error in processing pipeline: {str(e)}"
        print(f"\nERROR: {error_msg}")
        import traceback
        traceback.print_exc()
        
        status["success"] = False
        status["message"] = "Processing failed"
        status["error"] = error_msg
        
        return None, {}, status


def save_questions_to_csv(data: list, output_path: str) -> str:
    """
    Save questionnaire results to CSV file.
    
    Args:
        data: List of dictionaries containing question-answer data
        output_path: Full path for output CSV file
    
    Returns:
        Path to saved CSV file
    """
    if not data or not isinstance(data, list):
        raise ValueError("Data must be a non-empty list of dictionaries")
    
    # Create directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    os.makedirs(output_dir, exist_ok=True)
    
    # Extract CSV headers from first record
    fieldnames = data[0].keys()
    
    # Write CSV
    with open(output_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    
    print(f"CSV saved: {output_path}")
    return output_path


def batch_process_files(
    file_list: list,
    project_code: str,
    question_db_path: str,
    model_key: str,
    output_base_dir: str = r"C:\Users\cheth\Documents\save"
):
    """
    Process multiple JSON files in batch.
    
    Args:
        file_list: List of dictionaries with file info:
            [
                {
                    "json_path": "path/to/file1.json",
                    "file_code": "TXT_110303"
                },
                ...
            ]
        project_code: Project identifier
        question_db_path: Path to question database
        model_key: OpenAI API key
        output_base_dir: Base output directory
    
    Returns:
        List of processing results
    """
    results = []
    
    print("="*60)
    print(f"🔄 STARTING BATCH PROCESSING")
    print(f"Project: {project_code}")
    print(f"Files to process: {len(file_list)}")
    print("="*60)
    
    for i, file_info in enumerate(file_list, 1):
        json_path = file_info.get("json_path")
        file_code = file_info.get("file_code")
        
        print(f"\n[{i}/{len(file_list)}] Processing: {os.path.basename(json_path)}")
        print(f"  File Code: {file_code}")
        
        result, output_files, status = get_raw_answers_pipeline(
            json_file_path=json_path,
            project_code=project_code,
            file_code=file_code,
            question_db_path=question_db_path,
            model_key=model_key,
            output_base_dir=output_base_dir
        )
        
        results.append({
            "file": json_path,
            "file_code": file_code,
            "result": result,
            "output_files": output_files,
            "status": status
        })
        
        print(f"  Status: {'✅ Success' if status['success'] else '❌ Failed'}")
    
    print(f"\n🎉 BATCH PROCESSING COMPLETE!")
    print(f"Total files processed: {len(results)}")
    print(f"Successful: {sum(1 for r in results if r['status']['success'])}")
    print(f"Failed: {sum(1 for r in results if not r['status']['success'])}")
    
    return results


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Example 1: Single file processing
    print("EXAMPLE 1: SINGLE FILE PROCESSING")
    print("="*60)
    
    result, output_files, status = get_raw_answers_pipeline(
        json_file_path=r"C:\Users\cheth\Downloads\download\Owner_XUV700_N6J19045_TR_31-10-2025 14_10_20.json",
        project_code="DYQVSQ",
        file_code="TXT_110303",
        question_db_path=r"C:\Users\cheth\Downloads\download\qdb_prompts_251115_190133.csv",
        model_key="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",
        output_base_dir=r"C:\Users\cheth\Documents\save"
    )