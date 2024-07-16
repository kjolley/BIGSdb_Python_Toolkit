from datetime import datetime

def get_datestamp():
	return datetime.today().strftime('%Y-%m-%d')
	
def get_current_year():
	return datetime.today().strftime('%Y')