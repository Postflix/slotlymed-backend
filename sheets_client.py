"""
Google Sheets Client for SlotlyCare
Handles all interactions with Google Sheets database
"""

import gspread
from google.oauth2.service_account import Credentials
import json
import os
from datetime import datetime

class SheetsClient:
    def __init__(self):
        """Initialize Google Sheets client with service account credentials"""
        # Get credentials from environment variable
        creds_json = os.environ.get('GOOGLE_CREDENTIALS_JSON')
        
        if not creds_json:
            raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable not set")
        
        # Parse JSON credentials
        creds_dict = json.loads(creds_json)
        
        # Define scopes
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        
        # Create credentials
        credentials = Credentials.from_service_account_info(
            creds_dict,
            scopes=scopes
        )
        
        # Authorize gspread client
        self.client = gspread.authorize(credentials)
        
        # Get spreadsheet ID from environment
        self.spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        if not self.spreadsheet_id:
            raise ValueError("SPREADSHEET_ID environment variable not set")
        
        # Open spreadsheet
        self.spreadsheet = self.client.open_by_key(self.spreadsheet_id)
        
        # Get worksheets
        self.doctors_sheet = self.spreadsheet.worksheet('doctors')
        self.availability_sheet = self.spreadsheet.worksheet('availability')
        self.appointments_sheet = self.spreadsheet.worksheet('appointments')
        
        # Try to get users sheet, create if doesn't exist
        try:
            self.users_sheet = self.spreadsheet.worksheet('users')
        except gspread.exceptions.WorksheetNotFound:
            self.users_sheet = self.spreadsheet.add_worksheet(title='users', rows=1000, cols=10)
            self.users_sheet.append_row(['customer_id', 'email', 'password_hash', 'created_at'])
    
    # ==================== DOCTORS METHODS ====================
    
    def save_doctor(self, doctor_data):
        """
        Save or update doctor data
        
        Args:
            doctor_data (dict): Doctor information
                - id: unique identifier (e.g., "dr-joao")
                - name: doctor name
                - specialty: medical specialty
                - address: clinic address
                - phone: contact phone
                - email: contact email
                - logo_url: URL to logo image (optional)
                - color: theme color (hex)
                - language: interface language (en, pt, es, fr, de, it)
                - welcome_message: greeting message (optional)
                - link: unique link (same as id)
                - customer_id: Stripe customer ID (optional)
        
        Returns:
            dict: Success status and doctor ID
        """
        try:
            # Check if doctor already exists
            existing = self.get_doctor(doctor_data['id'])
            
            if existing:
                # Update existing doctor
                cell = self.doctors_sheet.find(doctor_data['id'])
                row_num = cell.row
                
                # Update row (now with 12 columns including customer_id)
                self.doctors_sheet.update(f'A{row_num}:L{row_num}', [[
                    doctor_data['id'],
                    doctor_data['name'],
                    doctor_data.get('specialty', ''),
                    doctor_data['address'],
                    doctor_data['phone'],
                    doctor_data['email'],
                    doctor_data.get('logo_url', ''),
                    doctor_data['color'],
                    doctor_data['language'],
                    doctor_data.get('welcome_message', ''),
                    doctor_data['link'],
                    doctor_data.get('customer_id', existing.get('customer_id', ''))
                ]])
                
                return {
                    'success': True,
                    'message': 'Doctor updated',
                    'doctor_id': doctor_data['id']
                }
            else:
                # Add new doctor
                self.doctors_sheet.append_row([
                    doctor_data['id'],
                    doctor_data['name'],
                    doctor_data.get('specialty', ''),
                    doctor_data['address'],
                    doctor_data['phone'],
                    doctor_data['email'],
                    doctor_data.get('logo_url', ''),
                    doctor_data['color'],
                    doctor_data['language'],
                    doctor_data.get('welcome_message', ''),
                    doctor_data['link'],
                    doctor_data.get('customer_id', '')
                ])
                
                return {
                    'success': True,
                    'message': 'Doctor created',
                    'doctor_id': doctor_data['id']
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_doctor(self, doctor_id):
        """
        Get doctor data by ID
        
        Args:
            doctor_id (str): Doctor unique identifier
        
        Returns:
            dict: Doctor data or None if not found
        """
        try:
            # Find doctor row
            cell = self.doctors_sheet.find(doctor_id)
            if not cell:
                return None
            
            # Get row data
            row_data = self.doctors_sheet.row_values(cell.row)
            
            # Map to dictionary
            return {
                'id': row_data[0],
                'name': row_data[1],
                'specialty': row_data[2] if len(row_data) > 2 else '',
                'address': row_data[3] if len(row_data) > 3 else '',
                'phone': row_data[4] if len(row_data) > 4 else '',
                'email': row_data[5] if len(row_data) > 5 else '',
                'logo_url': row_data[6] if len(row_data) > 6 else '',
                'color': row_data[7] if len(row_data) > 7 else '#3B82F6',
                'language': row_data[8] if len(row_data) > 8 else 'en',
                'welcome_message': row_data[9] if len(row_data) > 9 else '',
                'link': row_data[10] if len(row_data) > 10 else '',
                'customer_id': row_data[11] if len(row_data) > 11 else ''
            }
        
        except gspread.exceptions.CellNotFound:
            return None
        except Exception as e:
            print(f"Error getting doctor: {e}")
            return None
    
    def get_doctor_by_customer_id(self, customer_id):
        """
        Get doctor data by Stripe customer ID
        
        Args:
            customer_id (str): Stripe customer ID
        
        Returns:
            dict: Doctor data or None if not found
        """
        try:
            # Get all rows
            all_rows = self.doctors_sheet.get_all_values()[1:]  # Skip header
            
            for row in all_rows:
                if len(row) > 11 and row[11] == customer_id:
                    return {
                        'id': row[0],
                        'name': row[1],
                        'specialty': row[2] if len(row) > 2 else '',
                        'address': row[3] if len(row) > 3 else '',
                        'phone': row[4] if len(row) > 4 else '',
                        'email': row[5] if len(row) > 5 else '',
                        'logo_url': row[6] if len(row) > 6 else '',
                        'color': row[7] if len(row) > 7 else '#3B82F6',
                        'language': row[8] if len(row) > 8 else 'en',
                        'welcome_message': row[9] if len(row) > 9 else '',
                        'link': row[10] if len(row) > 10 else '',
                        'customer_id': row[11] if len(row) > 11 else ''
                    }
            
            return None
        
        except Exception as e:
            print(f"Error getting doctor by customer_id: {e}")
            return None
    
    def check_link_available(self, link, exclude_doctor_id=None):
        """
        Check if a link is available (not taken by another doctor)
        
        Args:
            link (str): Link to check
            exclude_doctor_id (str): Doctor ID to exclude from check (for updates)
        
        Returns:
            bool: True if available, False if taken
        """
        try:
            # Get all links (column K)
            links = self.doctors_sheet.col_values(11)[1:]  # Skip header
            
            if exclude_doctor_id:
                # Get all IDs (column A)
                ids = self.doctors_sheet.col_values(1)[1:]  # Skip header
                # Filter out the doctor being updated
                links = [l for i, l in enumerate(links) if ids[i] != exclude_doctor_id]
            
            return link not in links
        
        except Exception as e:
            print(f"Error checking link: {e}")
            return False
    
    # ==================== USERS METHODS ====================
    
    def save_user(self, user_data):
        """
        Save user data (for authentication)
        
        Args:
            user_data (dict):
                - customer_id: Stripe customer ID
                - email: user email
                - password_hash: hashed password
                - created_at: timestamp
        
        Returns:
            dict: Success status
        """
        try:
            # Check if user already exists
            existing = self.get_user(user_data['customer_id'])
            
            if existing:
                # Update existing user
                cell = self.users_sheet.find(user_data['customer_id'])
                row_num = cell.row
                
                self.users_sheet.update(f'A{row_num}:D{row_num}', [[
                    user_data['customer_id'],
                    user_data['email'],
                    user_data['password_hash'],
                    user_data.get('created_at', datetime.now().isoformat())
                ]])
                
                return {
                    'success': True,
                    'message': 'User updated'
                }
            else:
                # Add new user
                self.users_sheet.append_row([
                    user_data['customer_id'],
                    user_data['email'],
                    user_data['password_hash'],
                    user_data.get('created_at', datetime.now().isoformat())
                ])
                
                return {
                    'success': True,
                    'message': 'User created'
                }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_user(self, customer_id):
        """
        Get user data by customer ID
        
        Args:
            customer_id (str): Stripe customer ID
        
        Returns:
            dict: User data or None if not found
        """
        try:
            cell = self.users_sheet.find(customer_id)
            if not cell:
                return None
            
            row_data = self.users_sheet.row_values(cell.row)
            
            return {
                'customer_id': row_data[0],
                'email': row_data[1] if len(row_data) > 1 else '',
                'password_hash': row_data[2] if len(row_data) > 2 else '',
                'created_at': row_data[3] if len(row_data) > 3 else ''
            }
        
        except gspread.exceptions.CellNotFound:
            return None
        except Exception as e:
            print(f"Error getting user: {e}")
            return None
    
    # ==================== AVAILABILITY METHODS ====================
    
    def save_availability(self, doctor_id, slots):
        """
        Save availability slots for a doctor
        Clears existing slots and adds new ones
        
        Args:
            doctor_id (str): Doctor unique identifier
            slots (list): List of slot dictionaries with date, time, status
        
        Returns:
            dict: Success status
        """
        try:
            # Clear existing slots for this doctor
            self.clear_availability(doctor_id)
            
            # Add new slots
            rows_to_add = []
            for slot in slots:
                rows_to_add.append([
                    doctor_id,
                    slot['date'],  # Format: YYYY-MM-DD
                    slot['time'],  # Format: HH:MM
                    slot.get('status', 'available')  # Default to available
                ])
            
            # Batch append for performance
            if rows_to_add:
                self.availability_sheet.append_rows(rows_to_add)
            
            return {
                'success': True,
                'message': f'{len(rows_to_add)} slots saved',
                'slots_count': len(rows_to_add)
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def clear_availability(self, doctor_id):
        """
        Clear all availability slots for a doctor
        
        Args:
            doctor_id (str): Doctor unique identifier
        """
        try:
            # Get all doctor_ids (column A)
            cells = self.availability_sheet.findall(doctor_id, in_column=1)
            
            # Delete rows in reverse order (to maintain row numbers)
            for cell in reversed(cells):
                self.availability_sheet.delete_rows(cell.row)
        
        except Exception as e:
            print(f"Error clearing availability: {e}")
    
    def get_availability(self, doctor_id, date=None):
        """
        Get available slots for a doctor
        
        Args:
            doctor_id (str): Doctor unique identifier
            date (str): Optional date filter (YYYY-MM-DD)
        
        Returns:
            list: List of available slots
        """
        try:
            # Get all rows
            all_rows = self.availability_sheet.get_all_values()[1:]  # Skip header
            
            # Filter by doctor_id and status
            slots = []
            for row in all_rows:
                if len(row) >= 4 and row[0] == doctor_id and row[3] == 'available':
                    if date is None or row[1] == date:
                        slots.append({
                            'date': row[1],
                            'time': row[2],
                            'status': row[3]
                        })
            
            return slots
        
        except Exception as e:
            print(f"Error getting availability: {e}")
            return []
    
    def update_slot_status(self, doctor_id, date, time, status):
        """
        Update status of a specific slot
        
        Args:
            doctor_id (str): Doctor unique identifier
            date (str): Slot date (YYYY-MM-DD)
            time (str): Slot time (HH:MM)
            status (str): New status (available/booked)
        
        Returns:
            bool: Success status
        """
        try:
            # Find the slot
            all_rows = self.availability_sheet.get_all_values()[1:]  # Skip header
            
            for i, row in enumerate(all_rows):
                if len(row) >= 3 and row[0] == doctor_id and row[1] == date and row[2] == time:
                    # Update status (column D, row is i+2 because of header and 0-index)
                    self.availability_sheet.update_cell(i + 2, 4, status)
                    return True
            
            return False
        
        except Exception as e:
            print(f"Error updating slot status: {e}")
            return False
    
    # ==================== APPOINTMENTS METHODS ====================
    
    def create_appointment(self, appointment_data):
        """
        Create a new appointment
        
        Args:
            appointment_data (dict):
                - doctor_id: doctor unique identifier
                - patient_name: patient full name
                - patient_email: patient email
                - patient_phone: patient phone
                - date: appointment date (YYYY-MM-DD)
                - time: appointment time (HH:MM)
                - notes: optional notes
        
        Returns:
            dict: Success status and appointment ID
        """
        try:
            # Generate appointment ID
            all_appointments = self.appointments_sheet.get_all_values()[1:]  # Skip header
            appointment_id = len(all_appointments) + 1
            
            # Create timestamp
            created_at = datetime.now().isoformat()
            
            # Add appointment
            self.appointments_sheet.append_row([
                str(appointment_id),
                appointment_data['doctor_id'],
                appointment_data['patient_name'],
                appointment_data['patient_email'],
                appointment_data['patient_phone'],
                appointment_data['date'],
                appointment_data['time'],
                appointment_data.get('notes', ''),
                created_at
            ])
            
            # Update slot status to booked
            self.update_slot_status(
                appointment_data['doctor_id'],
                appointment_data['date'],
                appointment_data['time'],
                'booked'
            )
            
            return {
                'success': True,
                'message': 'Appointment created',
                'appointment_id': appointment_id
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_appointments(self, doctor_id):
        """
        Get all appointments for a doctor
        
        Args:
            doctor_id (str): Doctor unique identifier
        
        Returns:
            list: List of appointments
        """
        try:
            all_rows = self.appointments_sheet.get_all_values()[1:]  # Skip header
            
            appointments = []
            for row in all_rows:
                if len(row) >= 9 and row[1] == doctor_id:
                    appointments.append({
                        'id': row[0],
                        'doctor_id': row[1],
                        'patient_name': row[2],
                        'patient_email': row[3],
                        'patient_phone': row[4],
                        'date': row[5],
                        'time': row[6],
                        'notes': row[7],
                        'created_at': row[8]
                    })
            
            return appointments
        
        except Exception as e:
            print(f"Error getting appointments: {e}")
            return []
