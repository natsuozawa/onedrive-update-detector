# OneDrive update detector

Monitors a OneDrive directory for uploads of new files.

Due to OneDrive API restrictions, this service will only monitor files under `/me/drive/approot`, which usually corresponds to `/Apps/app_name` in your personal OneDrive.

Also due to OneDrive API restrictions, this service will instead:

1. Detect any folders where files with the configured file type(s) were created or updated
2. Downloads the newest files from the folders detected above.

You can specify which files to check for in the configuration below. Note that the webhook which starts this process is only triggered upon new file creation or file deletion.

The service requires the file write permission to create the approot special directory.

This service only supports storing credentials for one user.

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

```
FLASK_APP = name of app
FILE_TYPES = file types to look for, comma separated - e.g. ".csv,.db"
DOWNLOAD_LOCATION = path to the folder where files are downloaded to.
MODE = debug or production
```

The following are variables related to the Microsoft API. See the [documentation](https://docs.microsoft.com/en-us/graph/auth-v2-user) for more details.

```
TENANT = "common", "organizations", or "consumers"
APPLICATION_ID = corresponds to client_id, obtained from Azure Active Directory
REDIRECT_URL = corresponds to redirect_uri, should be set to localhost:5000 for development with ngrok.
APPLICATION_URL = url of the app (no paths) - eg. "https://123.jp.ngrok.io"
CLIENT_SECRET = client secret registered in the Azure Active Directory.
```

# Development

```
$ ngrok http 5000
$ python3 index.py
```

# Production

```
$ waitress-serve --port=5000 index:app
```
