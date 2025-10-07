import pandas as pd
from typing import List
from src.models.report import Report
from src.utils.logging_config import app_logger
import os
from datetime import datetime


class ReportGeneratorService:
    """
    Service for generating structured reports in Excel format with matched Arshin data.
    """
    
    def __init__(self):
        # Define the required columns for the output report
        self.report_columns = [
            'ID в Аршине',           # vri_id
            'Организация-поверитель',  # org_title
            'Регистрационный номер типа СИ',  # mit_number
            'Наименование типа СИ',    # mit_title
            'Обозначение типа СИ',     # mit_notation
            'Заводской номер',        # mi_number
            'Дата поверки',           # verification_date
            'Действительна до',       # valid_date
            'Номер свидетельства',    # result_docnum
            'Статус обработки',       # processing_status
            'Номер строки в исходном файле'  # excel_source_row
        ]
    
    def generate_report(self, reports: List[Report], output_path: str = None) -> str:
        """
        Generate an Excel report from a list of Report objects.
        
        Args:
            reports: List of Report objects to include in the report
            output_path: Optional path for the output file (will be generated if not provided)
            
        Returns:
            Path to the generated Excel file
        """
        if not output_path:
            # Generate a default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"results/report_{timestamp}.xlsx"
        
        try:
            # Convert Report objects to a list of dictionaries for pandas
            report_data = []
            for report in reports:
                row = {
                    'ID в Аршине': report.arshin_id or '',
                    'Организация-поверитель': report.org_title or '',
                    'Регистрационный номер типа СИ': report.mit_number or '',
                    'Наименование типа СИ': report.mit_title or '',
                    'Обозначение типа СИ': report.mit_notation or '',
                    'Заводской номер': report.mi_number or '',
                    'Дата поверки': report.verification_date or '',
                    'Действительна до': report.valid_date or '',
                    'Номер свидетльства': report.result_docnum or '',
                    'Статус обработки': report.processing_status.value,
                    'Номер строки в исходном файле': report.excel_source_row
                }
                report_data.append(row)
            
            # Create a DataFrame from the report data
            df = pd.DataFrame(report_data, columns=self.report_columns)
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Write to Excel file
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')
                
                # Get the workbook and worksheet to adjust column widths
                worksheet = writer.sheets['Results']
                
                # Adjust column widths for better readability
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    # Set a minimum width and cap at a reasonable maximum
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            app_logger.info(f"Generated report with {len(reports)} records at {output_path}")
            return output_path
            
        except Exception as e:
            app_logger.error(f"Error generating report at {output_path}: {e}")
            raise
    
    def generate_summary_report(self, reports: List[Report], output_path: str = None) -> str:
        """
        Generate a summary report with statistics about the processing results.
        
        Args:
            reports: List of Report objects to summarize
            output_path: Optional path for the output file (will be generated if not provided)
            
        Returns:
            Path to the generated Excel file with summary
        """
        if not output_path:
            # Generate a default filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"results/summary_report_{timestamp}.xlsx"
        
        try:
            # Calculate summary statistics
            total_records = len(reports)
            matched_count = sum(1 for r in reports if r.processing_status == 'MATCHED')
            not_found_count = sum(1 for r in reports if r.processing_status == 'NOT_FOUND')
            error_count = sum(1 for r in reports if r.processing_status == 'ERROR')
            invalid_format_count = sum(1 for r in reports if r.processing_status == 'INVALID_CERT_FORMAT')
            
            # Create summary data
            summary_data = {
                'Статистика': [
                    'Всего записей',
                    'Найдено в Аршине',
                    'Не найдено в Аршине', 
                    'С ошибками',
                    'С недействительным форматом сертификата',
                    'Процент найденных записей'
                ],
                'Значение': [
                    total_records,
                    matched_count,
                    not_found_count,
                    error_count,
                    invalid_format_count,
                    f"{(matched_count/total_records*100):.2f}%" if total_records > 0 else "0%"
                ]
            }
            
            # Create summary DataFrame
            summary_df = pd.DataFrame(summary_data)
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            
            # Write summary to Excel file
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                summary_df.to_excel(writer, index=False, sheet_name='Summary')
                
                # Also include the detailed results in a second sheet
                if reports:
                    # Convert Report objects to a list of dictionaries for pandas
                    report_data = []
                    for report in reports:
                        row = {
                            'ID в Аршине': report.arshin_id or '',
                            'Организация-поверитель': report.org_title or '',
                            'Регистрационный номер типа СИ': report.mit_number or '',
                            'Наименование типа СИ': report.mit_title or '',
                            'Обозначение типа СИ': report.mit_notation or '',
                            'Заводской номер': report.mi_number or '',
                            'Дата поверки': report.verification_date or '',
                            'Действительна до': report.valid_date or '',
                            'Номер свидетельства': report.result_docnum or '',
                            'Статус обработки': report.processing_status.value,
                            'Номер строки в исходном файле': report.excel_source_row
                        }
                        report_data.append(row)
                    
                    # Write detailed report to second sheet
                    detailed_df = pd.DataFrame(report_data, columns=self.report_columns)
                    detailed_df.to_excel(writer, index=False, sheet_name='Detailed Results')
                    
                    # Format the detailed results sheet
                    detailed_worksheet = writer.sheets['Detailed Results']
                    
                    # Adjust column widths for better readability
                    for column in detailed_worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        
                        # Set a minimum width and cap at a reasonable maximum
                        adjusted_width = min(max_length + 2, 50)
                        detailed_worksheet.column_dimensions[column_letter].width = adjusted_width
            
            app_logger.info(f"Generated summary report at {output_path}")
            return output_path
            
        except Exception as e:
            app_logger.error(f"Error generating summary report at {output_path}: {e}")
            raise
    
    def validate_report_data(self, reports: List[Report]) -> tuple[bool, str]:
        """
        Validate the report data before generating the report.
        
        Args:
            reports: List of Report objects to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if not reports:
                return True, "No reports to validate, which is acceptable"
            
            for i, report in enumerate(reports):
                if not hasattr(report, 'processing_status'):
                    return False, f"Report at index {i} is missing processing_status"
                
                if report.excel_source_row is None:
                    return False, f"Report at index {i} is missing excel_source_row"
            
            return True, ""
        except Exception as e:
            return False, f"Validation error: {str(e)}"