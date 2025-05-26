from flask import Flask, render_template, request, jsonify
from waitress import serve
from functions import names_and_photos, get_QR_filename, get_photo_filename, list_of_seeds, list_of_generics, list_of_companies
from functions import update_database_list, save_user_input_img, save_feedback, BUCKET_NAME, ensure_valid_file_name
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

    matches = []
    file_names = []
    with open('static/seedList.txt', 'r') as file:
        for line in file:
            if line.split(":")[0] in seed_type:
                if len(line.split(":")) > 1:
                    varieties = line.split(":")[1]
                    varieties = varieties.split(",")

                    for variety in varieties:
                        item = variety.strip() + " " + line.split(":")[0].strip()
                        matches.append(item)
                else:
                    matches.append(line.strip())
   
    photo_urls = names_and_photos(matches)  

    return render_template('seed-info-page.html', seed=seed_type.capitalize(), matches = photo_urls, companies=list_of_companies())

@app.route('/pdf-viewer')
def pdf_viewer():
    variety = request.args.get('variety').title() 
    filename = get_photo_filename(variety)
    photo_url = f"https://{BUCKET_NAME}.s3.amazonaws.com/icons/{filename}"

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
    QR_link = request.form.get('QR-link')

    #confirm no blank inputs
    inputs = [generic_seed,specific_seed,company,QR_link]
    if any(len(ele)==0 for ele in inputs):
        expl="Missing an input. Make sure to fill out all areas on the form."
        return render_template('error.html', error="Missing value", expl=expl)
    
    # Secure the filename
    if user_file:
        ext = user_file.filename.rsplit('.', 1)[1].lower()
        file_name = specific_seed + " " + generic_seed
        file_name, file_path = ensure_valid_file_name(file_name,file_ext=ext,filepath="seed_imgs") 
        # Save file locally
        user_file.save(file_name)

        upload_file_bucket(file_name,'new-bucket-2341',file_path)
        #QR code do this later
        QR_file = requests.get(QR_link)
   
    seed_name = (specific_seed + " " + generic_seed).title()

    #render template
    return render_template('confirm-new-entry.html',seed_name=seed_name)

@app.route('/give-feedback')
def give_feedback():
    return render_template('give-feedback.html')

@app.route('/confirm-feedback')
def confirm_feedback():
    feedback = request.args.get('feedback')
    save_feedback(feedback)
    return render_template('confirm-feedback.html')

if __name__ == '__main__':
    app.run(host = "0.0.0.0", port = 8000)
    #serve(app, host="0.0.0.0", port=8000)