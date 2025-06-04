# Purpose
_Project started March 2025_\
To make operations more efficient for my work at GrowNYC, I decided to create a hub for materials I use often. The main feature of this hub is a "seed look-up", where the user can search for a seed variety, obtain its image and QR code linking to the webpage about the variety, and the user will have the option to print a label sheet pdf in the dimensions of Avery 5160 30-count sheet.

## The Web Service
My website is a flask application hosted by Render. Please allow the website to load for a few seconds, as my free tier subscription means it spins down after 15 minutes of inactivity. 

## The Data Base

### Initial seed options
All images, QR codes and seed names are stored in an AWS S3 bucket (as image or text files) managed by myself, and are retrieved from the bucket to be displayed on the website. Over 1,000 seed varieties from the seed company Johnny's Seeds have already been uploaded to the S3 bucket as I obtained information on the company's many seed varieties via webscraping with BeautifulSoup and commenced a batch upload. The file "batchUpload.py" contains the code for this process.

### User input
Users may add a seed to the database via a form on the website. They must input the seed's generic variety (e.g. basil), specific variety (e.g. red rubin), seed company (default is Johnny's Seeds), image file and optionally a link to the seed's information page. The backend will retrieve these inputs and upload the image file with its according name (file naming proceduring described below) to the S3 bucket, as well as create a QR code if a link was provided using python's qrcode library and uploading it as well. The seed name will be added to master list of seed varieties stored as a txt file in the S3 bucket.

### Naming procedures
The seedList.txt file contains all seed varieties in the database. Each seed type occupies it's own line on the file, and specific varieties of that seed are separated by commas put after the generic name with a colon. For example:
- sunflower: autumn beauty, teddy bear

For easy access to photos and QR codes for each variety, the files will be named as such:
- {specific variety}{general}{QR/icon}, with hyphens in between each word. E.g., "black-cherry-tomato.jpg"
- The default will be Johnny's Seeds for QR codes unless otherwise specified.

## PDF viewer current functionality
Users can print out a Avery 5160-formatted label sheet for a specific seed variety. The user must select the seed name, seed company and sow date. The default image on the label will be the plant photo, but the user can opt to change it to the QR code for the seed's website.

## Next steps
Next steps for pdf viewer:
- allow for user copy and paste of plant images instead of file upload
- allow for user to edit the size of text on labels (dynamic css stylesheet)
- create options for the pdf viewer to edit the seed name to be different than what is presented in the database (though users can get around this by uploading a photo with the exact seed name they want displayed on the label sheet)
- allow for quick create of pdf with solely user clipboard information, overstepping any database search or upload steps
- maybe: allow user to specify other label sheet dimensions (not Avery 5160)
- maybe: allow user to specify number of labels needed (e.g., only 15 and not the full 30)
- maybe: allow user to select multiple seed varieties and their respective label counts they want printed on one sheet (e.g., 16 labels for Lemon Basil, 4 labels for Bok Choy, 10 labels blank)

