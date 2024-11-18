def connect_google_sheets(spreadsheet_id: str):
   
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name("C:/Users/HP/Desktop/AI Agent2.0/venv/credentials.json", scope)
    client = gspread.authorize(credentials)
    
    sheet = client.open_by_key(spreadsheet_id)
    worksheet = sheet.get_worksheet(0) 
    
    data = worksheet.get_all_values()
    return data
