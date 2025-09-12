# ai_services/file_service.py
import pandas as pd
import json
import logging
from pathlib import Path
from typing import Dict
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

logger = logging.getLogger("ai_services")


class FileService:
    def __init__(self):
        self.upload_path = settings.MEDIA_ROOT / "uploads"
        self.upload_path.mkdir(parents=True, exist_ok=True)

        # Supported file types and their processors
        self.processors = {
            ".csv": self._process_csv,
            ".xlsx": self._process_excel,
            ".xls": self._process_excel,
            ".txt": self._process_text,
            ".json": self._process_json,
            ".pdf": self._process_pdf,
        }

    def _clean_data_for_json(self, data):
        """Clean data to ensure JSON serialization"""
        try:
            if isinstance(data, dict):
                return {str(k): self._clean_data_for_json(v) for k, v in data.items()}
            elif isinstance(data, list):
                return [self._clean_data_for_json(item) for item in data]
            elif isinstance(data, (int, float, str, bool, type(None))):
                # Handle NaN and infinity values
                if isinstance(data, float):
                    if pd.isna(data) or pd.isinf(data):
                        return None
                return data
            elif hasattr(data, "dtype"):  # numpy/pandas types
                if pd.isna(data) or pd.isinf(data):
                    return None
                if hasattr(data, "item"):  # numpy scalar
                    return data.item()
                return str(data)
            elif hasattr(data, "to_dict"):  # pandas objects
                try:
                    return self._clean_data_for_json(data.to_dict())
                except (AttributeError, TypeError, ValueError) as e:
                    logger.debug(f"Failed to convert pandas object to dict: {e}")
                    return str(data)
            elif hasattr(data, "tolist"):  # numpy arrays
                return self._clean_data_for_json(data.tolist())
            else:
                return str(data)
        except Exception as e:
            logger.error(f"Error cleaning data for JSON: {e}")
            return str(data)

    def save_uploaded_file(self, file, session_id: str) -> Dict:
        """Save uploaded file and return file info"""
        try:
            # Generate unique filename
            file_extension = Path(file.name).suffix.lower()
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{session_id}_{timestamp}_{file.name}"

            # Save file
            file_path = default_storage.save(
                f"uploads/{filename}", ContentFile(file.read())
            )
            full_path = default_storage.path(file_path)

            return {
                "success": True,
                "filename": file.name,
                "saved_filename": filename,
                "file_path": file_path,
                "full_path": full_path,
                "file_size": file.size,
                "file_type": file_extension[1:] if file_extension else "unknown",
                "mime_type": getattr(file, "content_type", "application/octet-stream"),
            }

        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return {"success": False, "error": str(e)}

    def process_file(self, file_path: str, file_type: str) -> Dict:
        """Process uploaded file and extract content"""
        try:
            file_extension = (
                f".{file_type}" if not file_type.startswith(".") else file_type
            )

            if file_extension not in self.processors:
                return {
                    "success": False,
                    "error": f"Unsupported file type: {file_type}",
                }

            processor = self.processors[file_extension]
            result = processor(file_path)

            return result

        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return {"success": False, "error": str(e)}

    def _process_csv(self, file_path: str) -> Dict:
        """Process CSV file"""
        try:
            logger.info(f"Processing CSV file: {file_path}")
            df = pd.read_csv(file_path)
            logger.info(f"CSV loaded: {len(df)} rows, {len(df.columns)} columns")

            # Basic analysis
            logger.info("Creating basic analysis...")
            analysis = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": list(df.columns),
                "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
                "missing_values": {
                    col: int(count) for col, count in df.isnull().sum().items()
                },
                "memory_usage": int(df.memory_usage(deep=True).sum()),
            }
            logger.info(f"Analysis created: {analysis}")

            # Sample data
            sample = df.head(10).to_dict("records")

            # Summary statistics for numeric columns
            if not df.select_dtypes(include=["number"]).empty:
                describe_df = df.describe()
                numeric_summary = {}
                for col in describe_df.columns:
                    numeric_summary[col] = {
                        "count": float(describe_df[col]["count"]),
                        "mean": float(describe_df[col]["mean"]),
                        "std": float(describe_df[col]["std"]),
                        "min": float(describe_df[col]["min"]),
                        "25%": float(describe_df[col]["25%"]),
                        "50%": float(describe_df[col]["50%"]),
                        "75%": float(describe_df[col]["75%"]),
                        "max": float(describe_df[col]["max"]),
                    }
            else:
                numeric_summary = {}

            # Clean the data for JSON serialization
            # Handle NaN values in the DataFrame before conversion
            df_clean = df.fillna("N/A")  # Replace NaN with 'N/A' string

            clean_sample = self._clean_data_for_json(sample)
            clean_full_data = self._clean_data_for_json(
                df_clean.head(100).to_dict("records")
            )  # Limit to first 100 rows

            result = {
                "success": True,
                "file_type": "csv",
                "content": df.to_string(max_rows=1000),  # Limit for display
                "data": clean_sample,
                "analysis": analysis,
                "numeric_summary": numeric_summary,
                "full_data": clean_full_data,  # Cleaned data for AI processing
            }

            # Final validation: ensure the result is JSON serializable
            try:
                import json

                json.dumps(result)
                logger.info("JSON validation passed")
            except Exception as e:
                logger.error(f"JSON validation failed: {e}")
                # If validation fails, create a simplified result
                result = {
                    "success": True,
                    "file_type": "csv",
                    "content": f"CSV file with {len(df)} rows and {len(df.columns)} columns",
                    "data": [],  # Empty data to avoid serialization issues
                    "analysis": {
                        "rows": len(df),
                        "columns": len(df.columns),
                        "column_names": list(df.columns),
                    },
                    "message": "File processed successfully (simplified output due to data complexity)",
                }

            logger.info("CSV processing completed successfully")
            logger.info(f"Result keys: {list(result.keys())}")
            logger.info(f"Sample data type: {type(result['data'])}")
            logger.info(f"Analysis type: {type(result['analysis'])}")

            return result

        except Exception as e:
            return {"success": False, "error": f"Error processing CSV: {str(e)}"}

    def _process_excel(self, file_path: str) -> Dict:
        """Process Excel file"""
        try:
            # Read all sheets
            excel_file = pd.ExcelFile(file_path)
            sheets_data = {}

            for sheet_name in excel_file.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet_name)
                # Clean the data for JSON serialization
                clean_sheet_data = self._clean_data_for_json(
                    df.head(10).to_dict("records")
                )
                sheets_data[sheet_name] = {
                    "data": clean_sheet_data,
                    "rows": int(len(df)),
                    "columns": int(len(df.columns)),
                    "column_names": list(df.columns),
                }

            result = {
                "success": True,
                "file_type": "excel",
                "sheets": sheets_data,
                "sheet_names": excel_file.sheet_names,
                "content": f"Excel file with {len(excel_file.sheet_names)} sheets: {', '.join(excel_file.sheet_names)}",
            }

            # Final validation: ensure the result is JSON serializable
            try:
                import json

                json.dumps(result)
                logger.info("Excel JSON validation passed")
            except Exception as e:
                logger.error(f"Excel JSON validation failed: {e}")
                # If validation fails, create a simplified result
                result = {
                    "success": True,
                    "file_type": "excel",
                    "sheet_names": excel_file.sheet_names,
                    "content": f"Excel file with {len(excel_file.sheet_names)} sheets: {', '.join(excel_file.sheet_names)}",
                    "message": "File processed successfully (simplified output due to data complexity)",
                }

            return result

        except Exception as e:
            return {"success": False, "error": f"Error processing Excel: {str(e)}"}

    def _process_text(self, file_path: str) -> Dict:
        """Process text file"""
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            # Basic text analysis
            lines = content.split("\n")
            words = content.split()

            analysis = {
                "characters": len(content),
                "words": len(words),
                "lines": len(lines),
                "encoding": "utf-8",
            }

            return {
                "success": True,
                "file_type": "text",
                "content": content,
                "analysis": analysis,
            }

        except Exception as e:
            return {"success": False, "error": f"Error processing text file: {str(e)}"}

    def _process_json(self, file_path: str) -> Dict:
        """Process JSON file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Clean the data for JSON serialization
            clean_data = self._clean_data_for_json(data)

            # Basic JSON analysis
            analysis = {
                "type": type(data).__name__,
                "size": len(data) if isinstance(data, (list, dict)) else 1,
            }

            if isinstance(data, dict):
                analysis["keys"] = list(data.keys())
            elif isinstance(data, list) and data and isinstance(data[0], dict):
                analysis["keys"] = list(data[0].keys()) if data else []

            return {
                "success": True,
                "file_type": "json",
                "content": json.dumps(clean_data, indent=2)[:5000],  # Limit for display
                "data": clean_data,
                "analysis": analysis,
            }

        except Exception as e:
            return {"success": False, "error": f"Error processing JSON: {str(e)}"}

    def _process_pdf(self, file_path: str) -> Dict:
        """Process PDF file - basic implementation"""
        try:
            # For PDF processing, you would typically use libraries like PyPDF2 or pdfplumber
            # This is a placeholder implementation
            return {
                "success": False,
                "error": "PDF processing not implemented. Please install PyPDF2 or pdfplumber.",
            }

        except Exception as e:
            return {"success": False, "error": f"Error processing PDF: {str(e)}"}

    def process_folder_path(self, folder_path: str) -> Dict:
        """Process files in a folder path"""
        try:
            folder = Path(folder_path)
            if not folder.exists() or not folder.is_dir():
                return {
                    "success": False,
                    "error": f"Folder does not exist: {folder_path}",
                }

            files_info = []
            supported_files = []

            for file_path in folder.rglob("*"):
                if file_path.is_file():
                    file_extension = file_path.suffix.lower()
                    file_info = {
                        "name": file_path.name,
                        "path": str(file_path),
                        "size": file_path.stat().st_size,
                        "extension": file_extension,
                        "supported": file_extension in self.processors,
                    }
                    files_info.append(file_info)

                    if file_extension in self.processors:
                        supported_files.append(file_path)

            return {
                "success": True,
                "folder_path": folder_path,
                "total_files": len(files_info),
                "supported_files": len(supported_files),
                "files": files_info,
                "supported_extensions": list(self.processors.keys()),
            }

        except Exception as e:
            logger.error(f"Failed to process folder {folder_path}: {e}")
            return {"success": False, "error": str(e)}

    def get_file_summary(self, file_path: str) -> str:
        """Get a text summary of file content for AI processing"""
        try:
            file_extension = Path(file_path).suffix.lower()

            if file_extension == ".csv":
                df = pd.read_csv(file_path)
                return f"""CSV File Summary:
- Rows: {len(df)}
- Columns: {len(df.columns)}
- Column names: {", ".join(df.columns)}
- Sample data:\n{df.head().to_string()}"""

            elif file_extension in [".xlsx", ".xls"]:
                excel_file = pd.ExcelFile(file_path)
                summaries = []
                for sheet in excel_file.sheet_names:
                    df = pd.read_excel(file_path, sheet_name=sheet)
                    summaries.append(
                        f"Sheet '{sheet}': {len(df)} rows, {len(df.columns)} columns"
                    )
                return "Excel File Summary:\n" + "\n".join(summaries)

            elif file_extension == ".txt":
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()[:2000]  # First 2000 characters
                return f"Text File Content (first 2000 chars):\n{content}"

            elif file_extension == ".json":
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return f"JSON File Summary:\nType: {type(data).__name__}\nContent preview:\n{json.dumps(data, indent=2)[:1000]}"

            else:
                return f"Unsupported file type: {file_extension}"

        except Exception as e:
            return f"Error reading file: {str(e)}"

    def cleanup_old_files(self, days: int = 7):
        """Clean up old uploaded files"""
        try:
            cutoff_date = pd.Timestamp.now() - pd.Timedelta(days=days)
            upload_folder = Path(settings.MEDIA_ROOT) / "uploads"

            deleted_count = 0
            for file_path in upload_folder.glob("*"):
                if file_path.is_file():
                    file_time = pd.Timestamp.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_date:
                        file_path.unlink()
                        deleted_count += 1

            logger.info(f"Cleaned up {deleted_count} old files")
            return deleted_count

        except Exception as e:
            logger.error(f"Failed to cleanup files: {e}")
            return 0

    def process_file_for_rag(
        self,
        session_id: str,
        file_path: str,
        file_type: str,
        file_name: str,
        file_id: str,
    ) -> Dict:
        """
        Process file for RAG system using ChromaDB

        Args:
            session_id: Chat session ID
            file_path: Path to the file
            file_type: Type of file
            file_name: Name of the file
            file_id: Database file ID

        Returns:
            RAG processing results
        """
        try:
            from .chroma_service import ChromaService

            chroma_service = ChromaService()
            result = chroma_service.process_file_for_rag(
                session_id, file_path, file_type, file_name, file_id
            )

            return result

        except Exception as e:
            logger.error(f"Error processing file for RAG: {e}")
            return {"success": False, "error": str(e), "chunks": []}
