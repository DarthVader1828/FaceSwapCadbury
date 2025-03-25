import os
import requests
import http.client
import json
import io
import base64
import flask
from flask import Flask, render_template, request
from PIL import Image
import logging
import certifi
from dotenv import load_dotenv
load_dotenv()
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Limit upload size to 16 MB

logging.basicConfig(level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s')

# Ensure the upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

IMGBB_API_KEY = os.getenv('IMGBB_API_KEY')
def upload_to_imgbb(file):
    """Upload image to ImgBB and return the image URL."""
    url = "https://api.imgbb.com/1/upload"
    try:
        payload = {
            'key': IMGBB_API_KEY,
            'image': base64.b64encode(file.read()).decode('utf-8')  # Convert the image to base64
        }
        response = requests.post(url, data=payload)
        response_json = response.json()
        print("API Response:", response_json) # For debugging
        if "error" in response_json and response_json["error"]:
            error_message = response_json["error"]
            logging.error("Magic API error: %s", error_message)

            return flask.Response(f"""
                <script>
                    alert("Error: {error_message}\\nPlease try again.");
                    window.location.href = "/";
                </script>
            """, mimetype='text/html')
        if response_json.get('success'):
            return response_json['data']['url']
        else:
            print("Error uploading image:", response_json.get('error', 'Unknown error'))
            return None
    except Exception as e:
        print("Error handling image:", e)
        return None
    
MAGIC_API_URL = "https://api.magicapi.dev/api/v1/magicapi/faceswap/faceswap-direct"
MAGIC_API_KEY = os.getenv('MAGIC_API_KEY')

def send_email(email, name, gender, generated_image_url, uploaded_image_url, target_image):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders
    import smtplib
    sender_email = os.getenv('SENDER_EMAIL') 
    sender_password = os.getenv('SENDER_PASSWORD') 
    recipient_emails = ["shazam20000@gmail.com", email]
    subject = f"""Face Swap Result - {name}"""
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails)
    msg['Subject'] = subject
    body = f"""Face Swap Result

👤 Name: {name}
📧 Email: {email}
🚻 Gender: {gender}

🖼️ User Image: {uploaded_image_url}
🎯 Target Image: {target_image}
✨ Generated Image: {generated_image_url}
    """
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP('smtp.gmail.com', 587) as server:  # Replace with your SMTP server
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_emails, msg.as_string())

@app.route('/', methods=['GET', 'POST'])
def index():
    target_images = [
        "https://i.ibb.co/LzC7SFjV/Drinks-coca-cola-posters-wallace-beery.jpg",
        "https://i.ibb.co/N2Qzr2L5/myeracad.webp",
        "https://i.ibb.co/5gKch6pZ/My-Cadbury-Era-4.jpg",
        "https://i.ibb.co/cSC4tqZY/myera.jpg",
        "https://i.ibb.co/Xk6rkJTw/myera-Cadbury-poster-1.jpg",
        "https://i.ibb.co/gLMdMQjq/20240724-My-Cadbury-Era-3.webp",
        "https://i.ibb.co/vx3f0qL3/coca-cola-delicieux-32720-coca-cola-vintage-poster-jpg-960x0-q85-subsampling-2-upscale.jpg",
        "https://i.ibb.co/MkTN5R1P/myeracadburygirl.jpg",
        "https://i.ibb.co/ZzgjrQcG/My-Cadbury-Era-2.jpg",
        "https://i.ibb.co/Q7D4g0TF/myeracadbury.jpg"
    ]

    if request.method == 'POST':
    # Check for uploaded file or selfie
        if 'image' in request.files and request.files['image'].filename:
            file = request.files['image']
        elif 'selfie_file' in request.files and request.files['selfie_file'].filename:
            file = request.files['selfie_file']
        else:
            logging.error("No image or selfie file uploaded.")
            return "No file uploaded", 400
        
        name = request.form['name']
        email = request.form['email']
        gender = request.form['gender']
        target_image = request.form['target_image']
        logging.info("User Info - Name: %s, Email: %s, Gender: %s", name, email, gender)
        logging.info("Target image selected: %s", target_image)
        # Upload the user's image to ImgBB
        uploaded_image_url = upload_to_imgbb(file)
        logging.info("Uploaded image URL: %s", uploaded_image_url)
        
        if uploaded_image_url:
            payload = {
                "input": {
                    "swap_image": uploaded_image_url,
                    "target_image": target_image
                }
            }

            headers = {
                'x-magicapi-key': MAGIC_API_KEY,
                'content-type': "application/json"
            }
            
            response = requests.post(MAGIC_API_URL, json=payload, headers=headers)
            response_text = response.text
            logging.debug("Magic API response: %s", response_text)
            response_json=response.json()
            if "error" in response_json and response_json["error"]:
                error_message = response_json["error"]
                logging.error("Magic API error: %s", error_message)

                return flask.Response(f"""
                    <script>
                        alert("Error: {error_message}\\nPlease try again.");
                        window.location.href = "/";
                    </script>
                """, mimetype='text/html')

            output_data = response_json.get("output", "")
            if output_data.startswith("data:image"):
                base64_image = output_data.split(",", 1)[1]  # Get just the base64 part
            else:
                base64_image = output_data
            missing_padding = len(base64_image) % 4
            if missing_padding:
                base64_image += '=' * (4 - missing_padding)
            decoded_image = base64.b64decode(base64_image)
            file_like = io.BytesIO(decoded_image)
            generated_image_url = upload_to_imgbb(file_like)
            send_email(email,name,gender,generated_image_url,uploaded_image_url,target_image)
            return render_template('result.html', image_url=generated_image_url)

    return render_template('index.html', target_images=target_images)

@app.route('/result', methods=['GET'])
def result():
    return render_template('result.html')

if __name__ == '__main__':
    app.run(debug=True)
