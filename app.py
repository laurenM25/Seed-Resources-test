from flask import Flask, render_template, request
from waitress import serve
from functions import names_and_photos, get_QR_filename, get_photo_filename, list_of_seeds, list_of_generics, list_of_companies
from functions import update_database_list, save_user_input_img, BUCKET_NAME

app = Flask(__name__)

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
    #get info
    generic_seed = request.form.get('generic-seed').lower()
    specific_seed = request.form.get('specific-seed').lower()
    company = request.form.get('company').title()
    QR_link = request.form.get('QR-link')

    #confirm no blank inputs
    inputs = [generic_seed,specific_seed,company,QR_link]
    if any(len(ele)==0 for ele in inputs):
        expl="Missing an input. Make sure to fill out all areas on the form."
        return render_template('error.html', error="Missing value", expl=expl)

    plant_image = request.files['fileUpload']

    #add entry to database
    update = update_database_list(generic_seed,specific_seed,company,QR_link,plant_image)
    if isinstance(update,str):
        expl = "An error occured when updating the database list with the image. System error."
        return render_template('error.html', error=update, expl=expl)

    seed_name = (specific_seed + " " + generic_seed).title()

    #render template
    return render_template('confirm-new-entry.html',seed_name=seed_name)

if __name__ == '__main__':
    app.run(host = "0.0.0.0", port = 8000)
    #serve(app, host="0.0.0.0", port=8000)