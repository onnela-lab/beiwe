import os

os.environ['BEIWE_URL'] = 'https://studies.beiwe.org' #Insert server name here (e.g. https://studies.beiwe.org)
os.environ['BEIWE_USERNAME'] = '' # Insert username to Beiwe deployment (what you enter when you log in to https://studies.beiwe.org or whatever Beiwe deployment you're using)
os.environ['BEIWE_PASSWORD'] = '' # Insert password to Beiwe Deployment (what you enter as the password when you log in to your Beiwe deployment
os.environ['BEIWE_ACCESS_KEY'] = '' #Insert API access key. To get this, click "manage credentials" at the top of the Beiwe deployment, then under "Manage API Credentials" click "Generate A New API Key". The secret key is only shown once, so record it now.
os.environ['BEIWE_SECRET_KEY'] = '' #Insert API secret key

# Beiwe API keys are universal, so the pair above also works on the summary-statistics
# ("Tableau") endpoints. There is nothing extra to generate, and the separate
# "Manage Tableau Credentials" section these used to come from no longer exists.
# Replace these two lines with explicit values only if you are on an older deployment
# that still issues a separate Tableau key.
os.environ['TABLEAU_ACCESS_KEY'] = os.environ['BEIWE_ACCESS_KEY']
os.environ['TABLEAU_SECRET_KEY'] = os.environ['BEIWE_SECRET_KEY']
