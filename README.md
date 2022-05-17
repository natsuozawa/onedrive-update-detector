# OneDrive DB update detector 

Monitors a OneDrive directory for uploads of new CSV and DB files.

This app only supports storing credentials for one user.

# Virtual environment

This app uses Python's virtual environment feature. To enable:

```
$ source venv/bin/activate
```

# Installation

Install dependencies.

```
$ pip3 install -r requirements.txt
```

Install ngrok from [here](https://ngrok.com).

# Azure Active Directory app registration
This app needs to be registered on Azure Active Directory. In order to use personal accounts, select the option that allows all users to use the service.

## Generate client secret
Generate a client secret from the certificates and secrets section. Copy this into the configuration as shown below.

## Add permissions
Add a permission in Azure Active Directory from the API permissions section. This app requires the following delegated Microsoft Graph API permissions to be added to the app.

```
offline_acess
Files.Read
User.Read
```

# Configuration

This app requires the following environment variables to be configured. 

The following are variables related to the Microsoft API. See the [documentation](https://docs.microsoft.com/en-us/graph/auth-v2-user) for more details.

```
TENANT = "common", "organizations", or "consumers"
APPLICATION_ID = corresponds to client_id, obtained from Azure Active Directory
APPLICATION_URL = url of the app (no paths)
CLIENT_SECRET = client secret registered in the Azure Active Directory.
```

# Development

```
$ ngrok http 5000
$ python3 app.py
```