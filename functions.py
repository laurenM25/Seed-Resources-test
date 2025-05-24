from PIL import Image
from werkzeug.utils import secure_filename
import boto3
import qrcode
import os
from datetime import datetime, timezone, timedelta
import requests

#checking time drift - DEBUGGING
# Local server time
print("Local UTC:", datetime.now(timezone.utc))

# AWS server time via HTTP Date header
response = requests.head('https://s3.amazonaws.com')
print("AWS Server time:", response.headers['Date'])


# Initialize boto3 S3 client (for remote storage of photos)
session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_DEFAULT_REGION")
)

#check if properly fetched on Render
print(session.get_credentials().get_frozen_credentials())

s3 = session.client('s3')
BUCKET_NAME = 'grownyc-app-assets'

def generate_presigned_url(key, content_type, expiration=3600): #use presigned url 
    return s3.generate_presigned_url(
        'put_object',
        Params={
            'Bucket': BUCKET_NAME,
            'Key': key,
            'ContentType': content_type
        },
        ExpiresIn=expiration
    )

def names_and_photos(matches):
    my_dict = {}

    base = f"https://{BUCKET_NAME}.s3.us-east-1.amazonaws.com/icons/"
    for match in matches:
        key = match.strip().replace(" ", "-")
        my_dict[match] = [
        base + key + "-QR.png",
        base + key + ".jpg"
        ]
    
    return my_dict

def get_QR_filename(variety_name): #input a string, output a string
    variety_name = variety_name.strip().lower()
    return variety_name.replace(" ", "-") + "-QR.png"

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

    # Make sure the directory exists
    save_path = os.path.join('static', 'icons')
    os.makedirs(save_path, exist_ok=True)

    #save to AWS
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)

    s3_key = f'icons/{filename}'
    presigned_url = generate_presigned_url(s3_key, 'image/png')

    # Upload via HTTP PUT
    response = requests.put(
        presigned_url,
        data=buf,
        headers={'Content-Type': 'image/png'}
    )

    if response.status_code != 200:
        raise Exception(f"Failed to upload QR code: {response.text}")

    return f"https://{BUCKET_NAME}.s3.us-east-1.amazonaws.com/icons/{filename}"

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

def save_user_input_img(filepath, file):

    if file:
        filename = secure_filename(filepath)
        s3_key = f'icons/{filename}'
        presigned_url = generate_presigned_url(s3_key, file.content_type)
        response = requests.put(
            presigned_url,
            data=file,
            headers={'Content-Type': file.content_type}
        )
        if response.status_code != 200:
            raise Exception(f"Failed to upload image: {response.text}")
        return f"https://{BUCKET_NAME}.s3.us-east-1.amazonaws.com/icons/{filename}"
    return None

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
