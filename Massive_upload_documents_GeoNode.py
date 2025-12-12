# -*- coding: utf-8 -*-
"""
Created on Mon Nov 10 16:22:02 2025

@author: alessandro.lotti
Python code for massive upload of documents on GeoNode using url. 
Furthermore, the code updates the abstract and some metadata using PATCH. 
The code has been writen by Alessandro lotti for INFO/RAC

"""

import requests
import csv
import re
import json

 
GEONODE_URL = "https://geonodewebsite.com" #<--  write your geonode instance
USERNAME = "user"         # <-- write your user. N.B. the user will be the owner of the document
PASSWORD = "password"     # <-- write your password
CSV_PATH = r"C:\path\myfile.csv" # <-- location of your CSV file withe the list of documents. 
#The file should be structured with the following columns: 'title', 'date', 'lang', 'url'
owner = USERNAME
 
# 1️ Create a login session
#---------------------------
session = requests.Session()

# 2 take CSRF token from login page
#---------------------------
login_url = f"{GEONODE_URL}/account/login/"
r = session.get(login_url)
csrftoken = session.cookies.get("csrftoken")
if not csrftoken:
    raise RuntimeError("❌ Nessun CSRF token ricevuto dal server.")

# 3️ Finalize login
#---------------------------
login_data = {
    "csrfmiddlewaretoken": csrftoken,
    "login": USERNAME,
    "password": PASSWORD,
}
headers = {"Referer": login_url}
r = session.post(login_url, data=login_data, headers=headers)

if "sessionid" not in session.cookies:
    raise RuntimeError("❌ Login failed! check username and password.")
print("✅ Login riuscito, sessione creata.")

# 4️ Upload the documents from CSV
#---------------------------------
with open(CSV_PATH, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f, delimiter=';', skipinitialspace=True)
    print("👉 Campi letti:", reader.fieldnames)
    for i, row in enumerate(reader, start=1):
        csrftoken = session.cookies.get("csrftoken")


        title = (row.get("title") or "").strip()
        url = (row.get("url") or "").strip()
        lang= row.get("lang", "").upper() 
        date= row.get("date", "")


        abstract_raw = f"{title} \n --- Domain: {owner}  - Year: {date} - Language: {lang}"
        abstract_text = str(abstract_raw or "").strip().replace("\\n", "\n")

        if not title or not url:
            print(f"⚠️ row {i} skipped: title or url missing → {row}")
            continue

        data = {
            "title": title,
            "abstract": abstract_text,
            "doc_url": url,
            "doc_type": "document",
            "extension": ".pdf",
        }

        headers = {
            "Referer": f"{GEONODE_URL}/documents/upload/",
            "X-CSRFToken": csrftoken,
        }

        r = session.post(
            f"{GEONODE_URL}/documents/upload?no__redirect=true",
            data=data,
            headers=headers,
        )

        if r.status_code in (200, 201):
            
            data = r.json()
            doc_url = data.get("url")
            m = re.search(r'/document/(\d+)', doc_url)
            doc_id = m.group(1) if m else None
            print("✅ Document created with ID:", doc_id)
         
            uploaded_docs.append({
                "title": title,
                "doc_id": doc_id,
                "url": doc_url,
                "year": date
            })
            
# 5 Update the abstract
#---------------------------------
            update_url = f"{GEONODE_URL}/api/v2/documents/{doc_id}/"
            headers.update({
                "X-CSRFToken": session.cookies.get("csrftoken"),
                "Content-Type": "application/json"
            })
         
            raw_lang = (lang or "").lower().strip()            # if there are multilanguages es. "eng,fra,spa"....
            first_lang = raw_lang.split(",")[0].strip()         # it takes the first one → "eng"
         
            payload = {
                "abstract": abstract_text,
                "language": first_lang.lower(),
            }
            
            r = session.patch(update_url, data=json.dumps(payload), headers=headers)
            
            if r.status_code in (200, 204):
                print(f"✅ Abstract updated for document ID {doc_id}")
            else:
                print(f"❌ Error for update ({r.status_code}): {r.text[:500]}")


        else:
            print(f"❌ Riga {i}: errore {r.status_code} → {r.text[:500]}")

# 6 Export the list of ID into excel
df = pd.DataFrame(uploaded_docs)
output_path = "document_upload_id.xlsx"
df.to_excel(output_path, index=False)

print("📁 File Excel created:", output_path)


