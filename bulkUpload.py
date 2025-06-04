#write generics to file, with colon after and all of its specifics

#for each specific, create image file with appropriate name and save to AWS S3 bucket

#save text files on AWS bucket and use in get_seed_list() function instead of scraping web each time 

from functions import add_scraped_to_seed_list
import requests
from urllib.parse import urlparse
import qrcode
from botocore.exceptions import ClientError
import dotenv
import boto3
import os
import ast
import re

dotenv.load_dotenv()

aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')

s3 = boto3.client(service_name = 's3', region_name="us-east-1", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)


def create_seedList_file():
    seed_df = add_scraped_to_seed_list()

    with open("seedList.txt","w") as file:
        for generic in seed_df['name'].str.lower().str.strip():
            specific_varieties_list = specific_list(generic,seed_df)
            specifics_string = ", ".join(specific_varieties_list).title()

            newLine = generic.title() + ": " + specifics_string + "\n"
            file.write(newLine)

    #now upload text file to bucket
    upload_file_bucket("seedList.txt")

def specific_list(generic, seed_df):
    if not isinstance(generic,str):
        raise ValueError("Could not create specific list for the provided generic because it is not type string")
    else:
        #locate row of generic
        generic_row = seed_df[seed_df['name'].str.lower() == generic]
        if generic_row.empty:
            raise NameError
        l = []
        specific_varieties = generic_row["specific-varieties"].values[0]
        if isinstance(specific_varieties,str):
            specific_varieties = ast.literal_eval(specific_varieties)

        for i,dict in enumerate(specific_varieties):
            if isinstance(dict, list):
                dict = dict[0]
            variety = dict["variety-name"].replace(generic,"").lower().strip()
            variety = variety + " " + generic
            l.append(variety)
            # now get and upload photos
            url_to_upload(variety,dict["QR-url"],dict["plant-photo-url"])
        return l
    #now, get all values from the "variety-name" key for each dictionary
    #also, prevent this case:  "Basil": "Basil" (if generic == specific){replace specific with "Common"}
    #basically, touch up on the specifics list before appending them

sample_specific_varieties = "[{'variety-name': 'Blossom Pearl', 'QR-url': 'https://www.johnnyseeds.com/flowers/agrostemma-corn-cockle/blossom-pearl-agrostemma-seed-5074.html', 'plant-photo-url': 'https://www.johnnyseeds.com/dw/image/v2/BJGJ_PRD/on/demandware.static/-/Sites-jss-master/default/dwe052d88c/images/products/flowers/05074_01_blossom_pearl_agrostemma.jpg?sw=400&sh=400'}, {'variety-name': 'Ocean Pearls', 'QR-url': 'https://www.johnnyseeds.com/flowers/agrostemma-corn-cockle/ocean-pearls-agrostemma-seed-1105.html', 'plant-photo-url': 'https://www.johnnyseeds.com/dw/image/v2/BJGJ_PRD/on/demandware.static/-/Sites-jss-master/default/dw445960a3/images/products/flowers/01105_01_oceanpearlsclosehorz.jpg?sw=400&sh=400'}]"

def upload_file_bucket(file_name,bucket="new-bucket-2341",filepath=None):
    if filepath is None:
        filepath = file_name
    try:
        response = s3.upload_file(file_name,bucket,filepath)
    except ClientError as e:
        print("error uploading")
    print("successful uploading")

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

def upload_by_url(file_name, filepath, url):
    response = requests.get(url)
    if response.status_code == 200:
        with open(file_name, 'wb') as file:
            file.write(response.content)
        upload_file_bucket(file_name,'new-bucket-2341',filepath)
    else:
        print("did not get valid response from the url, so did not upload")
        raise Exception
    
def url_to_upload(seed_name,QR_url, photo_url):
    #upload plant photo
    file_name, file_path = ensure_valid_file_name(seed_name,url=photo_url,filepath="seed_imgs")
    upload_by_url(file_name, file_path, photo_url)

    #upload QR
    file_name_QR = file_name.split(".")[0] + "-QR" + f".{file_name.split(".")[1]}"
    create_qr_code(QR_url,file_name_QR)
    upload_file_bucket(file_name_QR,"new-bucket-2341",filepath=f"seed_qrs/{file_name_QR}")

    #delete local file
    delete_file(file_name)
    delete_file(file_name_QR)

def delete_file(file_name):
    try:
        os.remove(file_name)
    except FileNotFoundError:
        print("The QR or plant image file was not found, so could not delete.")
    except PermissionError:
        print("Error: Permission denied to delete QR or plant image file.")
    except OSError as e:
        print(f"Error: An unexpected error occurred: {e}.")

#url_to_upload()
#create_seedList_file()

def fix_my_mistake():
    response = s3.get_object(Bucket="new-bucket-2341", Key="seedList.txt")
    lines = response['Body'].read().decode('utf-8').splitlines()

    cleaned_lines = []

    for line in lines:
        if ":" not in line:
            continue  # skip invalid lines
        keyword, text = [part.strip() for part in line.split(":", 1)]

        specific_varieties = [v.strip() for v in text.split(",")]
        cleaned_varieties = []

        for variety in specific_varieties:
            # Remove any trailing duplicate of the keyword
            while variety.lower().endswith(f" {keyword.lower()}"):
                variety = variety[:-(len(keyword) + 1)].strip()

            if variety.lower() == keyword.lower():
                cleaned_varieties.append(variety)

            else: #add back the keyword once
                cleaned_varieties.append(f"{variety} {keyword}")

        cleaned_text = ", ".join(cleaned_varieties)
        cleaned_lines.append(f"{keyword}: {cleaned_text}\n")

    # Join cleaned content into a single string
    new_content = ''.join(cleaned_lines)

    with open("test-seedList", 'w', encoding='utf-8') as file:
        file.writelines(cleaned_lines)
    
#fix_my_mistake()
upload_file_bucket("seedList.txt")


def clean_filename(filename):
    # Normalize unicode dash to normal dash
    filename = filename.replace("–", "-")  # en dash to hyphen
    filename = filename.replace("—", "-")  # em dash to hyphen
    
    # Remove trademark symbol and other unwanted symbols
    filename = re.sub(r'[™®,]', '', filename)
    
    # Replace multiple dashes or underscores with single dash
    filename = re.sub(r'[-_]{2,}', '-', filename)
    
    # Remove spaces around dashes
    filename = re.sub(r'\s*-\s*', '-', filename)
    
    # Replace spaces with dash
    filename = re.sub(r'\s+', '-', filename)
    
    # Remove any characters not allowed in S3 keys (optional)
    # Allow letters, numbers, dash, underscore, dot
    filename = re.sub(r'[^a-zA-Z0-9\-_.]', '', filename)
    
    # Lowercase all (optional)
    filename = filename.lower()
    
    return filename

def rename_object(bucket, old_key, new_key):
    if old_key == new_key:
        return False  # no change
    
    print(f"Renaming:\n{old_key} -> {new_key}")
    
    # Copy old object to new key
    s3.copy_object(Bucket=bucket, CopySource={'Bucket': bucket, 'Key': old_key}, Key=new_key)
    
    # Delete old object
    s3.delete_object(Bucket=bucket, Key=old_key)
    
    return True

def main(): #will need to clean up image filenames ughhh that's what you get for trusting webscraping
    continuation_token = None
    while True:
        if continuation_token:
            response = s3.list_objects_v2(Bucket="new-bucket-2341", Prefix=prefix, ContinuationToken=continuation_token)
        else:
            response = s3.list_objects_v2(Bucket="new-bucket-2341", Prefix=prefix)

        contents = response.get('Contents', [])
        for obj in contents:
            old_key = obj['Key']
            filename = old_key.split('/')[-1]  # just the filename
            cleaned_filename = clean_filename(filename)
            
            # Compose new key, preserving folder prefix (if any)
            if '/' in old_key:
                new_key = old_key.rsplit('/', 1)[0] + '/' + cleaned_filename
            else:
                new_key = cleaned_filename
            
            rename_object("new-bucket-2341", old_key, new_key)
        
        if response.get('IsTruncated'):  # more results to fetch
            continuation_token = response.get('NextContinuationToken')
        else:
            break


