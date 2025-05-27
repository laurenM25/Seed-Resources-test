from flask import Flask, render_template, request, jsonify
from waitress import serve
from functions import names_and_photos, get_photo_filename, list_of_seeds, list_of_generics, list_of_companies, create_qr_code
from functions import save_feedback, BUCKET_NAME, ensure_valid_file_name, update_seed_list, delete_file
import requests
import os
from dotenv import load_dotenv
import boto3
from botocore.exceptions import ClientError

app = Flask(__name__)
load_dotenv()

aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID')
aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY')

s3 = boto3.client(service_name = 's3', region_name="us-east-1", aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
print(aws_access_key_id)

def upload_file_bucket(file_name,bucket="new-bucket-2341",filepath=None):
    if filepath is None:
        filepath = file_name
    try:
        response = s3.upload_file(file_name,bucket,filepath)
    except ClientError as e:
        print("error uploading")
        return jsonify({'error': 'error uploading'})
    print("successful uploading")
    return jsonify({'success': 'successfully uploaded'})

@app.route('/')
@app.route('/homepage')
def index():
    return render_template('homepage.html',seeds=list_of_seeds(), companies=list_of_companies())

@app.route('/seed-info-page')
def seed_info_page():
    seed_type = request.args.get('seed-type').lower()
    print(f"Fetching info for seed type: {seed_type}")

    matches = []
    response = s3.get_object(Bucket=BUCKET_NAME, Key="seedList.txt")
    content = response['Body'].read().decode('utf-8')
    lines = content.strip().split("\n")
    
    for line in lines:
        parts = line.split(":")
        if len(parts) < 2:
            continue
        generic_name = parts[0].strip().lower()
        if generic_name in seed_type:
            varieties = parts[1].split(",")
            for variety in varieties:
                matches.append(variety.strip().lower())  # full name

    photo_urls = names_and_photos(matches)  


    return render_template('seed-info-page.html', seed=seed_type.capitalize(), matches = photo_urls, companies=list_of_companies())

@app.route('/pdf-viewer')
def pdf_viewer():
    variety = request.args.get('variety').title() 
    isQR = request.args.get('QR_chosen')

    filename = get_photo_filename(variety,isQR=isQR)
    folder = "seed_imgs"

    if isQR:
        folder = "seed_qrs"
    photo_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/{folder}/{filename}"

    company = request.args.get('company')
    date = request.args.get('month') + " " +  request.args.get("year")

    return render_template('pdf-viewer.html', rows=10, columns=3, picture_url=photo_url, variety=variety, company=company, date=date)

@app.route('/add-seed')
def add_seed_page():
    return render_template('add-seed.html',seeds=list_of_seeds(), generics=list_of_generics(), companies=list_of_companies())

@app.route('/confirm-new-entry', methods=['POST'])
def confirm_entry_page():
    if 'fileUpload' not in request.files:
        return 'No file part in the request', 400

    user_file = request.files['fileUpload']
    generic_seed = request.form.get('generic-seed').lower()
    specific_seed = request.form.get('specific-seed').lower()
    company = request.form.get('company').title()
    exclude_QR = request.form.get('no-qr-link') 
    QR_link = request.form.get('QR-link')

    #confirm no blank inputs
    inputs = [generic_seed,specific_seed,company]
    if any(len(ele)==0 for ele in inputs):
        expl="Missing an input. Make sure to fill out all areas on the form."
        return jsonify({'html': render_template('error.html', error="Missing value", expl=expl)})
    
    if not exclude_QR and len(QR_link) == 0:
        return jsonify({'error': 'Please either provide a QR link or check "Exclude link."'})
    
    # Secure the filename
    if user_file:
        ext = user_file.filename.rsplit('.', 1)[1].lower()
        file_name = specific_seed + " " + generic_seed
        file_name, file_path = ensure_valid_file_name(file_name,file_ext=ext,filepath="seed_imgs") 
        # Save file locally
        user_file.save(file_name)
    else:
        return jsonify({'error': 'The file provided was empty or invalid."'})
    
    if not exclude_QR: #link and QR
        try:
            QR_file = requests.get(QR_link)
        except:
            return jsonify({'error': 'Invalid url. Please submit a valid url.'})
        file_name_QR = file_name.replace(f".{ext}", "") + "-QR" + f".{ext}"
        #create and save QR code
        createQR = create_qr_code(QR_link,file_name_QR)
        if createQR == Exception:
            return jsonify({'error': 'QR code was unable to be created.'})
        
        upload_file_bucket(file_name_QR,"new-bucket-2341",filepath=f"seed_qrs/{file_name_QR}")
   
    #upload plant image now that I know QR file is valid
    upload_file_bucket(file_name,'new-bucket-2341',file_path)

    #update text file
    update_seed_list(generic_seed, specific_seed, company, QR_link)

    #remove files locally
    delete_file(file_name)
    delete_file(file_name_QR)
    
    seed_name = (specific_seed + " " + generic_seed).title()

    #render template
    rendered_html = render_template('confirm-new-entry.html', seed_name=seed_name)
    return jsonify({
        'html': rendered_html,
        'seed_name': seed_name
    })

@app.route('/give-feedback')
def give_feedback():
    return render_template('give-feedback.html')

@app.route('/confirm-feedback', methods=["POST"])
def confirm_feedback():
    feedback = request.form.get('feedback')
    response = save_feedback(feedback)
    if response is ClientError:
        return Exception
    return "all good!"

if __name__ == '__main__':
    app.run(host = "0.0.0.0", port = 8000)
    #serve(app, host="0.0.0.0", port=8000)