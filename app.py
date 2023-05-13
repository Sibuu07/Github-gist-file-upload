from flask import Flask, render_template, request, redirect, url_for
import requests
import os
import base64


app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './temp/'
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # limit file size to 100 MB


@app.errorhandler(400)
def bad_request(e):
    return render_template('error.html', message='Bad request'), 400


@app.errorhandler(413)
def request_entity_too_large(e):
    return render_template('error.html', message='File size exceeds limit'), 413


def get_file_size(file):
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)
    return size
    

@app.route('/')
def home():
    return render_template('upload.html')


@app.route('/upload', methods=['POST'])
def upload():
    try:
        # get form data
        api_token = request.form['api_token']
        username = request.form['username']
        reponame = request.form['reponame']
        folder = request.form.get('folder', None)
        filepath = request.form.get('filepath', None)
        file = request.files['file']

        # check if file size is within limit
        file_size = get_file_size(file)
        if file_size > app.config['MAX_CONTENT_LENGTH']:
            return redirect(url_for('request_entity_too_large'))

        # if filepath is not provided, use filename as filepath
        if not filepath:
            filepath = file.filename

       # if folder is provided, create it if it does not exist
        if folder:
            folder_path = os.path.join(os.getcwd(), folder)
            if not os.path.exists(folder_path):
                os.makedirs(folder_path)
            filepath = os.path.join(folder, filepath)

        # check if file already exists in the specified path
        url = f'https://api.github.com/repos/{username}/{reponame}/contents/{filepath}'
        headers = {'Authorization': f'token {api_token}'}
        response = requests.get(url=url, headers=headers)

        if response.ok:
            # file already exists, rename file
            filename, extension = os.path.splitext(file.filename)
            count = 1
            new_filename = f"{filename}_{count}{extension}"
            while requests.get(f"https://api.github.com/repos/{username}/{reponame}/contents/{new_filename}", headers=headers).ok:
                count += 1
                new_filename = f"{filename}_{count}{extension}"
            filepath = new_filename
            message = f'File already exists, renamed file to {filepath}'
        else:
            message = 'Uploading file'

        # save file to temp directory
        file.save(filepath)

        # read file from temp directory and encode in base64
        with open(filepath, 'rb') as f:
            content = f.read()
            content_b64 = base64.b64encode(content).decode()

        # make API request to create or update file on GitHub
        url = f'https://api.github.com/repos/{username}/{reponame}/contents/{filepath}'
        data = {
            'message': message,
            'content': content_b64
        }
        
        response_github_api_call  = requests.put(url=url, headers=headers, json=data)

    except KeyError:
         return redirect(url_for('bad_request'))
       
    finally:

          if os.path.exists(filepath):
              os.remove(filepath)
              
          try:
              response_text_message_to_return_or_raise_value_error= response.text 
              response_json_message_to_return_or_raise_value_error= response.json()['message']  
          except:
              response_text_message_to_return_or_raise_value_error= 'Unknown error'
              response_json_message_to_return_or_raise_value_error = 'Unknown error'

    if response_github_api_call.ok:
        raw_url = response_github_api_call.json()['content']['download_url']
        return redirect(url_for('response', url=raw_url))
    else:         
      return render_template('error.html', message=response_text_message_to_return_or_raise_value_error)
      
@app.route('/response')
def response():
    try:
        url = request.args.get('url')
        return render_template('response.html', url=url)
    
    except KeyError:
         return redirect(url_for('bad_request'))
    
    
if __name__ == '__main__':
    app.run(debug=True)
