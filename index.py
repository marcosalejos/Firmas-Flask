import msal
import requests
from flask import Flask, make_response, request, session, redirect, url_for, render_template
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

app.config['SESSION_COOKIE_NAME'] = 'session'
app.config['SESSION_COOKIE_PATH'] = '/'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'


# Configura las credenciales de la aplicación registrada en Azure
CLIENT_ID = '5451bec6-4200-4326-99dc-fea4c8fb8be8'
CLIENT_SECRET = '2vM8Q~~0XN7Yxc.h1pka9G1qaPPXwEJEvfoPdbds'
AUTHORITY = 'https://login.microsoftonline.com/846f6db3-c6a6-4131-b084-cf6b63ab8af5'
SCOPE = ['User.Read']  # Puedes agregar otros permisos según tus necesidades

# Crea un objeto MSAL
app.config['MSAL_CLIENT'] = msal.ConfidentialClientApplication(
    CLIENT_ID, client_credential=CLIENT_SECRET
)

def get_user_info(clientID, clientSecret, tenantID, userID):

    token_url = f'https://login.microsoftonline.com/{tenantID}/oauth2/v2.0/token'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': clientID,
        'client_secret': clientSecret,
        'scope': 'https://graph.microsoft.com/.default'
    }
    response = requests.post(token_url, headers=headers, data=data)

    if response.status_code == 200:
        access_token = response.json()['access_token']
        endpoint = f'https://graph.microsoft.com/v1.0/users/{userID}?$select=displayName,mail,userPrincipalName,jobTitle,department,mobilePhone,businessPhones'
        headers = {'Authorization': f'Bearer {access_token}'}
        response = requests.get(endpoint, headers=headers)
        users_info = response.json()
        return users_info

@app.route('/', methods=['GET', 'POST'])
def index():
    if not session.get('user'):
        print("No se ha iniciado sesión")
        return redirect(url_for('login'))
    user = get_user_me()
    print(user)
    id = user['id']
    ext = user['businessPhones']
    if len(ext) == 0:
        ext = 'XX'
    data = {
        'Nombre': user['displayName'],
        'Departamento':  'Revisar',
        'Puesto':  user['jobTitle'],
        'Telefono':  user['mobilePhone'],
        'Ext':  user['businessPhones'][0],
        'Email': user['userPrincipalName']
    }
    raw_data = "";

    if request.method == 'POST':
        raw_data = request.form['raw_data']
    return render_template('firma.html', context=data, raw_data=raw_data)

@app.route('/login')
def login():
    auth_url = app.config['MSAL_CLIENT'].get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=url_for('callback', _external=True)
    )
    return redirect(auth_url)

@app.route('/callback')
def callback():
    # Procesa la respuesta de inicio de sesión
    if request.args.get('state') != session.get('state'):
        return redirect(url_for('index'))
    token = app.config['MSAL_CLIENT'].acquire_token_by_authorization_code(
    request.args['code'],
    scopes=SCOPE,
    redirect_uri=url_for('callback', _external=True)
)
    session['user'] = token.get('id_token_claims')
    return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    response = make_response(redirect(url_for('index')))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

def get_user_me():
    # Realiza una solicitud a Microsoft Graph para obtener información del usuario
    endpoint = 'https://graph.microsoft.com/v1.0/me'

    usr = app.config['MSAL_CLIENT'].get_accounts(session['user']['preferred_username'])
    token = app.config['MSAL_CLIENT'].acquire_token_silent(SCOPE, account=usr[0])
    headers = {'Authorization': f'Bearer {token["access_token"]}'}
    response = requests.get(endpoint, headers=headers)
    return response.json()

if __name__ == '__main__':
    app.run(host='localhost', debug=True)
