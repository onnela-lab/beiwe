import os

os.environ['BEIWE_URL'] = 'https://studies.beiwe.org' #Insert server name here (e.g. https://studies.beiwe.org)
os.environ['BEIWE_USERNAME'] = '' # Insert username to Beiwe deployment (what you enter when you log in to https://studies.beiwe.org or whatever Beiwe deployment you're using)
os.environ['BEIWE_PASSWORD'] = '' # Insert password to Beiwe Deployment (what you enter as the password when you log in to your Beiwe deployment
os.environ['BEIWE_ACCESS_KEY'] = '' #Insert data-download API access key. To get this, click "manage credentials" at the top of the Beiwe deployment, under "Generate New Data-Download API Access Credentials"
os.environ['BEIWE_SECRET_KEY'] = '' #Insert data-download API secret key
os.environ['TABLEAU_ACCESS_KEY'] = '' #Insert tableau API access key. To get this, click "manage credentials" at the top of the Beiwe deployment, then scroll down under "Manage Tableau Credentials" and click "Generate A New API Key"
os.environ['TABLEAU_SECRET_KEY'] = '' #Insert tableau API secret key

