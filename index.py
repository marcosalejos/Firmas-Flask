import msal
import requests
from flask import Flask, make_response, request, session, redirect, url_for, render_template
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)


# Configura las credenciales de la aplicación registrada en Azure
CLIENT_ID = ''
CLIENT_SECRET = ''
SCOPE = ['User.Read']  # Puedes agregar otros permisos según tus necesidades

# Crea un objeto MSAL
app.config['MSAL_CLIENT'] = msal.ConfidentialClientApplication(
    CLIENT_ID, client_credential=CLIENT_SECRET
)

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
        'Ext':  ext[0],
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
