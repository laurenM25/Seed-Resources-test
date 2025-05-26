from PIL import Image
from werkzeug.utils import secure_filename
import boto3
import qrcode
import os
from datetime import datetime, timezone, timedelta
import requests
from urllib.parse import urlparse
import re
from dotenv import load_dotenv
from botocore.exceptions import ClientError

#checking time drift - DEBUGGING
# Local server time
print("Local UTC:", datetime.now(timezone.utc))

# AWS server time via HTTP Date header
response = requests.head('https://s3.amazonaws.com')
print("AWS Server time:", response.headers['Date'])

load_dotenv()

aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')
BUCKET_NAME = "new-bucket-2341"

s3 = boto3.client(service_name = 's3', region_name="us-east-1", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)

def names_and_photos(matches):
    my_dict = {}

    base = f"https://{BUCKET_NAME}.s3.us-east-1.amazonaws.com/"
    for match in matches:
        key = match.strip().replace(" ", "-")
        my_dict[match] = [
        base + "seed_qrs/" + key + "-QR.jpg",
        base + "seed_imgs/" + key + ".jpg"
        ]
    return my_dict

def create_qr_code(data, filename):
    if not data.startswith("http://") and not data.startswith("https://"):
        raise ValueError("Invalid link — must start with http:// or https://")
    
    # Create a QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    # Add data to the QR code
    qr.add_data(data)
    qr.make(fit=True)

    # Create an image from the QR code instance
    img = qr.make_image(fill_color="black", back_color="white")
    try:
        img.save(filename)
    except Exception as e:
        print(f"in functions file: unable to save the QR image: {e}")
        return Exception

def get_photo_filename(variety_name):
    variety_name = variety_name.strip().lower()
    return variety_name.replace(" ", "-") + ".jpg"

def list_of_seeds(): #for the drop-down list on homepage
    seeds = []

    with open('static/seedList.txt', 'r') as file:
        for line in file:
            if len(line.split(":")) > 1:
                varieties = line.split(":")[1]
                varieties = varieties.split(",")

                for variety in varieties:
                    item = variety.strip() + " " + line.split(":")[0]
                    seeds.append(item)
            else:
                seeds.append(line)

    return seeds

def list_of_generics():
    seeds = []

    with open('static/seedList.txt', 'r') as file:
        for line in file:
            seeds.append(line.split(":")[0])

    return seeds

def list_of_companies():
    companies = ["Johnny's Seeds", "Hudson Valley Seed"]

    return companies

#update text list, or maybe redo app.py so it implements something like this:
"""
def update_database_list(generic, specific, company, QR_link, image): 
    name = specific + " " + generic
    image_name = get_photo_filename(name)
    QR_name = get_QR_filename(name)

    #create QR 
    create_qr_code(QR_link,QR_name)

    save = save_user_input_img(image_name,image)

    #now save name to file
    with open('static/seedList.txt', 'r+') as file:
        lines = file.readlines()  # Read all lines from the file

        matching_line = next((line for line in lines if line.split(":")[0].strip().lower() == generic.lower()), None)

        if matching_line:
            parts = matching_line.strip().split(":")
            varieties = parts[1].strip()
            # If the specific variety isn't already in the list, append it
            if specific.lower() not in varieties.lower():
                if len(varieties) > 1:
                    parts[1] = varieties + ", " + specific
                else:
                    parts[1] = specific
                # Update the line in the list
                updated_line = ":".join(parts) + "\n"
                lines[lines.index(matching_line)] = updated_line
        else:
            #  no matching line is found --> create a new line and append it
            lines.append(f"{generic}: {specific}\n")
        
        #update file with new lines
        file.seek(0)  # cursor moves back to the start of the file
        file.writelines(lines)  #add modified content back
        upload_txt_to_s3('static/seedList.txt')

    #DEAL WITH COMPANY LATER --> johnny default, but if Hudson, need that to reflect in filename
"""

def save_feedback(str,file_name="static/feedback.txt"):
    with open("static/feedback.txt", 'w') as f:
        f.write(str)
    
    file_path = f'feedback/feedback-{datetime.now(timezone.utc)}.txt'
    try:
        response = s3.upload_file(file_name,BUCKET_NAME,file_path)
    except ClientError as e:
        print("error uploading")
        return ClientError


#also not in use right now
"""
def upload_txt_to_s3(local_path): #update txt file in S3 bucket
    with open(local_path, 'rb') as f:
        s3_key = 'seedList.txt'
        presigned_url = generate_presigned_url(s3_key, 'text/plain')
        response = requests.put(
            presigned_url,
            data=f,
            headers={'Content-Type': 'text/plain'}
        )
        if response.status_code != 200:
            raise Exception(f"Failed to upload text file: {response.text}")
"""


def ensure_valid_file_name(file_name, url=None, file_ext=None, filepath=None):
    file_name = file_name.replace(" ", "-")
    file_name = re.sub(r'[<>:"/\\|?*]', '', file_name)

    if url:
        file_extension = os.path.splitext(urlparse(url).path)[1]
    if file_ext:
        if "." not in file_ext:
            file_extension = "." + file_ext
        else:
            file_extension = file_ext
    
    if len(file_name.split(".")) == 1:
        file_name += file_extension
    elif len(file_name.split(".")) == 2:
        #check if correct ending
        if file_name.split(".")[1] != file_extension.strip("."):
            file_name = file_name.split(".")[0] + file_extension
    else:
        file_name = file_name.replace(file_extension,"").replace(".","-") + file_extension

    if filepath: #ensure valid filepath leading up to where filename should be stored
        filepath = re.sub(r'[<>:"\\|?*]', '', filepath)
        if filepath[-1] == "/":
            filepath = filepath[:-1]
        filepath = filepath + "/" + file_name

    return file_name,filepath
